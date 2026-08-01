"""As-of Statcast / Stuff-style pitcher aggregates for starter_quality.

Fetches Baseball Savant pitch-level CSV in date chunks, caches on disk, and
aggregates pitcher metrics with a hard as-of cutoff (game_date − 1). No Odds API.
Pitch-sim remains gated off; this only rewrites starter_quality behind stuff_proxy.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode

import requests

SAVANT_SEARCH_CSV = "https://baseballsavant.mlb.com/statcast_search/csv"
MIN_PITCHES_STUFF = 200
_DEFAULT_CACHE = Path(__file__).resolve().parents[3] / "data" / "mlb" / "statcast_cache"
# Prefer env; else services/model-service/data/... (Railway --path-as-root), else repo-root data/.
CACHE_DIR = Path(os.getenv("MLB_STATCAST_CACHE_DIR") or _DEFAULT_CACHE)

# Approximate MLB pitcher means / spreads for z-scores (stuff → run-allowed factor).
LEAGUE_WHIFF_PCT = 0.112  # whiffs / pitches
LEAGUE_CHASE_PCT = 0.280  # swings / pitches outside zone
LEAGUE_ZONE_PCT = 0.475
LEAGUE_AVG_EV = 88.6
LEAGUE_BARREL_PCT = 0.072
SD_WHIFF = 0.028
SD_CHASE = 0.045
SD_ZONE = 0.035
SD_EV = 2.4
SD_BARREL = 0.025

# In-process cumulative index: season -> pitcher_id -> sorted (as_of_date_iso, metrics)
_PITCHER_CUMULATIVE: Dict[int, Dict[int, List[Tuple[str, Dict[str, float]]]]] = {}
_FETCHED_RANGES: Dict[int, List[Tuple[date, date]]] = {}
# Test / offline override: (season, pitcher_id, as_of_iso) -> metrics
_METRICS_OVERRIDE: Dict[Tuple[int, int, str], Dict[str, float]] = {}


def clear_statcast_stuff_caches() -> None:
    _PITCHER_CUMULATIVE.clear()
    _FETCHED_RANGES.clear()
    _METRICS_OVERRIDE.clear()


def set_stuff_metrics_override(
    *,
    season: int,
    pitcher_id: int,
    as_of: date,
    metrics: Dict[str, float],
) -> None:
    """Unit-test / offline injection (as-of join still uses as_of key)."""
    _METRICS_OVERRIDE[(int(season), int(pitcher_id), as_of.isoformat())] = dict(metrics)


def _cache_chunk_path(season: int, start: date, end: date) -> Path:
    return CACHE_DIR / str(season) / f"pitches_{start.isoformat()}_{end.isoformat()}.csv"


def _ensure_cache_dir(season: int) -> Path:
    path = CACHE_DIR / str(season)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _in_zone(zone: Any) -> bool:
    try:
        z = int(float(zone))
    except (TypeError, ValueError):
        return False
    return 1 <= z <= 9


def _is_whiff(description: str) -> bool:
    d = (description or "").lower()
    return d in {
        "swinging_strike",
        "swinging_strike_blocked",
        "foul_tip",
    }


def _is_swing(description: str) -> bool:
    d = (description or "").lower()
    if _is_whiff(d):
        return True
    return d.startswith("foul") or d.startswith("hit_into_play")


def _is_barrel(launch_speed: Optional[float], launch_angle: Optional[float]) -> bool:
    if launch_speed is None or launch_angle is None:
        return False
    # Statcast barrel approximation (EV ≥ 98 and LA in ~26–30 sweet spot grows with EV).
    if launch_speed < 98.0:
        return False
    return 8.0 <= launch_angle <= 50.0 and launch_speed >= (98.0 + abs(launch_angle - 26.0) * 0.3)


def aggregate_pitch_rows(rows: Iterable[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    """Aggregate pitch-level Savant rows → pitcher stuff metrics."""
    acc: Dict[int, Dict[str, float]] = {}
    for row in rows:
        try:
            pitcher_id = int(float(row.get("pitcher") or 0))
        except (TypeError, ValueError):
            continue
        if pitcher_id <= 0:
            continue
        bucket = acc.setdefault(
            pitcher_id,
            {
                "pitches": 0.0,
                "whiffs": 0.0,
                "swings": 0.0,
                "zone_pitches": 0.0,
                "chase_pitches": 0.0,
                "chase_swings": 0.0,
                "ev_sum": 0.0,
                "ev_n": 0.0,
                "barrels": 0.0,
                "bip": 0.0,
            },
        )
        bucket["pitches"] += 1.0
        desc = str(row.get("description") or "")
        zone = row.get("zone")
        in_zone = _in_zone(zone)
        if in_zone:
            bucket["zone_pitches"] += 1.0
        else:
            bucket["chase_pitches"] += 1.0
            if _is_swing(desc):
                bucket["chase_swings"] += 1.0
        if _is_whiff(desc):
            bucket["whiffs"] += 1.0
        if _is_swing(desc):
            bucket["swings"] += 1.0
        ev = row.get("launch_speed")
        la = row.get("launch_angle")
        try:
            ev_f = float(ev) if ev not in (None, "", "null") else None
        except (TypeError, ValueError):
            ev_f = None
        try:
            la_f = float(la) if la not in (None, "", "null") else None
        except (TypeError, ValueError):
            la_f = None
        if ev_f is not None and ev_f > 0:
            bucket["ev_sum"] += ev_f
            bucket["ev_n"] += 1.0
            bucket["bip"] += 1.0
            if _is_barrel(ev_f, la_f):
                bucket["barrels"] += 1.0
    out: Dict[int, Dict[str, float]] = {}
    for pid, b in acc.items():
        pitches = b["pitches"]
        if pitches <= 0:
            continue
        out[pid] = {
            "pitches": pitches,
            "whiff_pct": b["whiffs"] / pitches,
            "chase_pct": (b["chase_swings"] / b["chase_pitches"]) if b["chase_pitches"] > 0 else LEAGUE_CHASE_PCT,
            "zone_pct": b["zone_pitches"] / pitches,
            "avg_ev": (b["ev_sum"] / b["ev_n"]) if b["ev_n"] > 0 else LEAGUE_AVG_EV,
            "barrel_pct": (b["barrels"] / b["bip"]) if b["bip"] > 0 else LEAGUE_BARREL_PCT,
        }
    return out


def quality_from_stuff_metrics(metrics: Dict[str, float]) -> float:
    """Map stuff metrics → run-allowed factor (lower = better pitcher)."""
    whiff = float(metrics.get("whiff_pct") or LEAGUE_WHIFF_PCT)
    chase = float(metrics.get("chase_pct") or LEAGUE_CHASE_PCT)
    zone = float(metrics.get("zone_pct") or LEAGUE_ZONE_PCT)
    avg_ev = float(metrics.get("avg_ev") or LEAGUE_AVG_EV)
    barrel = float(metrics.get("barrel_pct") or LEAGUE_BARREL_PCT)

    z_whiff = (whiff - LEAGUE_WHIFF_PCT) / SD_WHIFF
    # Higher chase induction (batters chase) is good for pitcher → lower quality index.
    z_chase = (chase - LEAGUE_CHASE_PCT) / SD_CHASE
    z_zone = (zone - LEAGUE_ZONE_PCT) / SD_ZONE
    z_ev = (avg_ev - LEAGUE_AVG_EV) / SD_EV
    z_barrel = (barrel - LEAGUE_BARREL_PCT) / SD_BARREL

    quality = (
        1.0
        - 0.038 * z_whiff
        - 0.022 * z_chase
        - 0.012 * z_zone
        + 0.028 * z_ev
        + 0.030 * z_barrel
    )
    return max(0.82, min(1.18, round(quality, 4)))


def _parse_csv_text(text: str) -> List[Dict[str, str]]:
    if not text or text.strip().startswith("<!"):
        return []
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def fetch_statcast_pitch_chunk(
    *,
    start: date,
    end: date,
    season: int,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, str]]:
    """Fetch (or load cached) Savant pitch rows for [start, end]."""
    if end < start:
        return []
    path = _cache_chunk_path(season, start, end)
    if path.exists() and path.stat().st_size > 0:
        return _parse_csv_text(path.read_text(encoding="utf-8", errors="replace"))

    params = {
        "all": "true",
        "hfSea": f"{season}|",
        "hfGT": "R|",
        "game_date_gt": start.isoformat(),
        "game_date_lt": end.isoformat(),
        "player_type": "pitcher",
        "min_pitches": "1",
        "type": "details",
    }
    url = f"{SAVANT_SEARCH_CSV}?{urlencode(params)}"
    http = session or requests
    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            resp = http.get(
                url,
                timeout=90,
                headers={"User-Agent": "kosedge-mlb-statcast-cache/1.0"},
            )
            resp.raise_for_status()
            text = resp.text or ""
            _ensure_cache_dir(season)
            path.write_text(text, encoding="utf-8")
            meta = path.with_suffix(".meta.json")
            meta.write_text(
                json.dumps(
                    {
                        "source": "baseballsavant.mlb.com/statcast_search/csv",
                        "season": season,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "fetched_at": time.time(),
                        "bytes": len(text.encode("utf-8")),
                        "credit": "MLB Advanced Media / Baseball Savant (public CSV)",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            return _parse_csv_text(text)
        except Exception as exc:  # noqa: BLE001 — retry then degrade
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    if last_err:
        raise last_err
    return []


def _ranges_cover(covered: List[Tuple[date, date]], start: date, end: date) -> bool:
    if end < start:
        return True
    cur = start
    sorted_cov = sorted(covered)
    for a, b in sorted_cov:
        if b < cur:
            continue
        if a > cur:
            return False
        cur = max(cur, b + timedelta(days=1))
        if cur > end:
            return True
    return cur > end


def _mark_fetched(season: int, start: date, end: date) -> None:
    _FETCHED_RANGES.setdefault(season, []).append((start, end))


def _index_covers_through(season: int, through: date) -> bool:
    """True if compact as-of index already has points through `through`."""
    _load_index_if_needed(season)
    season_map = _PITCHER_CUMULATIVE.get(season) or {}
    if not season_map:
        return False
    cutoff = through.isoformat()
    # Require at least one pitcher with a point on/after through (season progressing).
    latest = max((series[-1][0] for series in season_map.values() if series), default="")
    return bool(latest) and latest >= cutoff


def ensure_statcast_pitches_through(*, season: int, through: date) -> None:
    """Ensure pitch CSV chunks exist from ~Mar 20 through `through` (inclusive)."""
    season_start = date(int(season), 3, 20)
    if through < season_start:
        return
    # Prefer committed compact index (no re-scrape) when it already covers `through`.
    if _index_covers_through(season, through):
        return
    covered = _FETCHED_RANGES.get(season) or []
    # Also treat existing cache files as covered.
    season_dir = CACHE_DIR / str(season)
    if season_dir.exists():
        for p in season_dir.glob("pitches_*.csv"):
            try:
                parts = p.stem.replace("pitches_", "").split("_")
                a = date.fromisoformat(parts[0])
                b = date.fromisoformat(parts[1])
                covered.append((a, b))
            except (IndexError, ValueError):
                continue
        _FETCHED_RANGES[season] = covered

    cursor = season_start
    while cursor <= through:
        chunk_end = min(cursor + timedelta(days=6), through)
        path = _cache_chunk_path(season, cursor, chunk_end)
        need_fetch = not path.exists() or path.stat().st_size == 0
        if need_fetch and not _ranges_cover(covered, cursor, chunk_end):
            rows = fetch_statcast_pitch_chunk(start=cursor, end=chunk_end, season=season)
            _ingest_rows_into_cumulative(season, rows)
            _mark_fetched(season, cursor, chunk_end)
        elif path.exists() and not _index_covers_through(season, chunk_end):
            # Rebuild index from on-disk CSV without re-hitting Savant.
            rows = _parse_csv_text(path.read_text(encoding="utf-8", errors="replace"))
            _ingest_rows_into_cumulative(season, rows)
            _mark_fetched(season, cursor, chunk_end)
        else:
            _mark_fetched(season, cursor, chunk_end)
        cursor = chunk_end + timedelta(days=1)


def _empty_raw() -> Dict[str, float]:
    return {
        "pitches": 0.0,
        "whiffs": 0.0,
        "chase_pitches": 0.0,
        "chase_swings": 0.0,
        "zone_pitches": 0.0,
        "ev_sum": 0.0,
        "ev_n": 0.0,
        "barrels": 0.0,
        "bip": 0.0,
    }


def _metrics_from_raw(tot: Dict[str, float]) -> Dict[str, float]:
    pitches = tot["pitches"]
    return {
        "pitches": pitches,
        "whiff_pct": tot["whiffs"] / pitches if pitches else LEAGUE_WHIFF_PCT,
        "chase_pct": (
            tot["chase_swings"] / tot["chase_pitches"] if tot["chase_pitches"] > 0 else LEAGUE_CHASE_PCT
        ),
        "zone_pct": tot["zone_pitches"] / pitches if pitches else LEAGUE_ZONE_PCT,
        "avg_ev": tot["ev_sum"] / tot["ev_n"] if tot["ev_n"] > 0 else LEAGUE_AVG_EV,
        "barrel_pct": tot["barrels"] / tot["bip"] if tot["bip"] > 0 else LEAGUE_BARREL_PCT,
    }


def _ingest_rows_into_cumulative(season: int, rows: List[Dict[str, str]]) -> None:
    """Fold chunk rows into per-pitcher daily cumulative series (by game_date)."""
    by_day: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        gd = str(row.get("game_date") or "")[:10]
        if not gd:
            continue
        by_day.setdefault(gd, []).append(row)

    season_map = _PITCHER_CUMULATIVE.setdefault(season, {})
    raw_path = CACHE_DIR / str(season) / "pitcher_raw_counts.json"
    raw: Dict[int, Dict[str, float]] = {}
    if raw_path.exists():
        try:
            loaded = json.loads(raw_path.read_text(encoding="utf-8"))
            for k, v in (loaded or {}).items():
                raw[int(k)] = {kk: float(vv) for kk, vv in v.items()}
        except Exception:
            raw = {}

    for gd in sorted(by_day):
        day_raw: Dict[int, Dict[str, float]] = {}
        for row in by_day[gd]:
            try:
                pid = int(float(row.get("pitcher") or 0))
            except (TypeError, ValueError):
                continue
            if pid <= 0:
                continue
            b = day_raw.setdefault(pid, _empty_raw())
            b["pitches"] += 1.0
            desc = str(row.get("description") or "")
            if _in_zone(row.get("zone")):
                b["zone_pitches"] += 1.0
            else:
                b["chase_pitches"] += 1.0
                if _is_swing(desc):
                    b["chase_swings"] += 1.0
            if _is_whiff(desc):
                b["whiffs"] += 1.0
            try:
                ev_f = float(row["launch_speed"]) if row.get("launch_speed") not in (None, "", "null") else None
            except (TypeError, ValueError, KeyError):
                ev_f = None
            try:
                la_f = float(row["launch_angle"]) if row.get("launch_angle") not in (None, "", "null") else None
            except (TypeError, ValueError, KeyError):
                la_f = None
            if ev_f is not None and ev_f > 0:
                b["ev_sum"] += ev_f
                b["ev_n"] += 1.0
                b["bip"] += 1.0
                if _is_barrel(ev_f, la_f):
                    b["barrels"] += 1.0

        for pid, inc in day_raw.items():
            tot = raw.setdefault(pid, _empty_raw())
            for k, v in inc.items():
                tot[k] = tot.get(k, 0.0) + v
            metrics = _metrics_from_raw(tot)
            series = season_map.setdefault(pid, [])
            if series and series[-1][0] == gd:
                series[-1] = (gd, metrics)
            elif series and series[-1][0] > gd:
                series = [x for x in series if x[0] != gd]
                series.append((gd, metrics))
                series.sort(key=lambda x: x[0])
                season_map[pid] = series
            else:
                series.append((gd, metrics))

    _ensure_cache_dir(season)
    raw_path.write_text(json.dumps({str(k): v for k, v in raw.items()}), encoding="utf-8")
    index_path = CACHE_DIR / str(season) / "pitcher_asof_index.json"
    compact = {
        str(pid): [{"d": d, **m} for d, m in series]
        for pid, series in season_map.items()
    }
    index_path.write_text(json.dumps(compact), encoding="utf-8")


def _load_index_if_needed(season: int) -> None:
    if season in _PITCHER_CUMULATIVE and _PITCHER_CUMULATIVE[season]:
        return
    index_path = CACHE_DIR / str(season) / "pitcher_asof_index.json"
    if not index_path.exists():
        _PITCHER_CUMULATIVE.setdefault(season, {})
        return
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        _PITCHER_CUMULATIVE.setdefault(season, {})
        return
    season_map: Dict[int, List[Tuple[str, Dict[str, float]]]] = {}
    for pid_s, points in (payload or {}).items():
        series: List[Tuple[str, Dict[str, float]]] = []
        for pt in points or []:
            d = str(pt.get("d") or "")
            if not d:
                continue
            series.append(
                (
                    d,
                    {
                        "pitches": float(pt.get("pitches") or 0),
                        "whiff_pct": float(pt.get("whiff_pct") or LEAGUE_WHIFF_PCT),
                        "chase_pct": float(pt.get("chase_pct") or LEAGUE_CHASE_PCT),
                        "zone_pct": float(pt.get("zone_pct") or LEAGUE_ZONE_PCT),
                        "avg_ev": float(pt.get("avg_ev") or LEAGUE_AVG_EV),
                        "barrel_pct": float(pt.get("barrel_pct") or LEAGUE_BARREL_PCT),
                    },
                )
            )
        season_map[int(pid_s)] = series
    _PITCHER_CUMULATIVE[season] = season_map


def get_pitcher_stuff_as_of(
    pitcher_id: int,
    *,
    as_of: date,
    season: Optional[int] = None,
    fetch_if_missing: bool = True,
) -> Optional[Dict[str, float]]:
    """Return stuff metrics using only pitches with game_date <= as_of − 1 day."""
    season_i = int(season or as_of.year)
    end_exclusive = as_of - timedelta(days=1)
    override = _METRICS_OVERRIDE.get((season_i, int(pitcher_id), as_of.isoformat()))
    if override is not None:
        return dict(override)

    if fetch_if_missing:
        try:
            ensure_statcast_pitches_through(season=season_i, through=end_exclusive)
        except Exception:
            # Degrade: use whatever index/cache already exists.
            pass

    _load_index_if_needed(season_i)
    series = (_PITCHER_CUMULATIVE.get(season_i) or {}).get(int(pitcher_id)) or []
    if not series:
        return None
    cutoff = end_exclusive.isoformat()
    chosen: Optional[Dict[str, float]] = None
    for d, metrics in series:
        if d <= cutoff:
            chosen = metrics
        else:
            break
    if chosen is None:
        return None
    if float(chosen.get("pitches") or 0) < MIN_PITCHES_STUFF:
        return None
    out = dict(chosen)
    out["as_of_pitches_through"] = cutoff
    return out
