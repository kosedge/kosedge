"""Batter–pitcher pitch-level / PA matchup (arsenal shape), not SP quality.

Distinct from:
  - matchup_mul (team split × season K/BB/GB)
  - starter_quality stuff_proxy / FIP / era_whip (run-allowed factor)

Uses as-of Statcast pitch-type mix + outcomes. Flag default OFF.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .mlb_statcast_stuff import (
    CACHE_DIR,
    _is_barrel,
    _is_whiff,
    _parse_csv_text,
    ensure_statcast_pitches_through,
)

MIN_PITCHES_ARSENAL = 180
LEAGUE_BREAK_WHIFF = 0.135
LEAGUE_HARD_BARREL = 0.085
LEAGUE_BREAK_PCT = 0.34

HARD_TYPES = frozenset({"FF", "SI", "FC", "FA"})
BREAK_TYPES = frozenset({"SL", "CU", "KC", "SV", "ST", "CS"})
SOFT_TYPES = frozenset({"CH", "FS", "FO", "SC", "KN"})

_ARSENAL_CUMULATIVE: Dict[int, Dict[int, List[Tuple[str, Dict[str, float]]]]] = {}
_ARSENAL_OVERRIDE: Dict[Tuple[int, int, str], Dict[str, float]] = {}

PITCH_MATCHUP_ENABLED = (
    str(os.getenv("MLB_PITCH_MATCHUP_ENABLED") or "false").strip().lower()
    in {"1", "true", "yes", "on"}
)


def apply_pitch_matchup_flag(enabled: Optional[bool] = None) -> bool:
    global PITCH_MATCHUP_ENABLED
    if enabled is not None:
        PITCH_MATCHUP_ENABLED = bool(enabled)
    return bool(PITCH_MATCHUP_ENABLED)


def get_pitch_matchup_enabled() -> bool:
    return bool(PITCH_MATCHUP_ENABLED)


def reset_pitch_matchup_from_env() -> bool:
    return apply_pitch_matchup_flag(
        str(os.getenv("MLB_PITCH_MATCHUP_ENABLED") or "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )


def clear_pitch_matchup_caches() -> None:
    _ARSENAL_CUMULATIVE.clear()
    _ARSENAL_OVERRIDE.clear()


def set_arsenal_metrics_override(
    *,
    season: int,
    pitcher_id: int,
    as_of: date,
    metrics: Dict[str, float],
) -> None:
    _ARSENAL_OVERRIDE[(int(season), int(pitcher_id), as_of.isoformat())] = dict(metrics)


def _empty_raw() -> Dict[str, float]:
    return {
        "pitches": 0.0,
        "hard": 0.0,
        "break": 0.0,
        "soft": 0.0,
        "break_whiffs": 0.0,
        "hard_bip": 0.0,
        "hard_barrels": 0.0,
    }


def _family(pitch_type: str) -> Optional[str]:
    pt = (pitch_type or "").strip().upper()
    if pt in HARD_TYPES:
        return "hard"
    if pt in BREAK_TYPES:
        return "break"
    if pt in SOFT_TYPES:
        return "soft"
    return None


def _metrics_from_raw(raw: Dict[str, float]) -> Dict[str, float]:
    pitches = float(raw.get("pitches") or 0.0)
    if pitches <= 0:
        return {
            "pitches": 0.0,
            "hard_pct": 0.0,
            "break_pct": 0.0,
            "soft_pct": 0.0,
            "break_whiff_pct": LEAGUE_BREAK_WHIFF,
            "hard_barrel_pct": LEAGUE_HARD_BARREL,
        }
    hard = float(raw.get("hard") or 0.0)
    brk = float(raw.get("break") or 0.0)
    soft = float(raw.get("soft") or 0.0)
    hard_bip = float(raw.get("hard_bip") or 0.0)
    return {
        "pitches": pitches,
        "hard_pct": hard / pitches,
        "break_pct": brk / pitches,
        "soft_pct": soft / pitches,
        "break_whiff_pct": (
            float(raw.get("break_whiffs") or 0.0) / brk if brk > 0 else LEAGUE_BREAK_WHIFF
        ),
        "hard_barrel_pct": (
            float(raw.get("hard_barrels") or 0.0) / hard_bip
            if hard_bip > 0
            else LEAGUE_HARD_BARREL
        ),
    }


def aggregate_arsenal_rows(rows: Iterable[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    acc: Dict[int, Dict[str, float]] = {}
    for row in rows:
        try:
            pitcher_id = int(float(row.get("pitcher") or 0))
        except (TypeError, ValueError):
            continue
        if pitcher_id <= 0:
            continue
        fam = _family(str(row.get("pitch_type") or ""))
        if fam is None:
            continue
        b = acc.setdefault(pitcher_id, _empty_raw())
        b["pitches"] += 1.0
        b[fam] += 1.0
        desc = str(row.get("description") or "")
        if fam == "break" and _is_whiff(desc):
            b["break_whiffs"] += 1.0
        if fam == "hard":
            try:
                ev = float(row["launch_speed"]) if row.get("launch_speed") not in (None, "", "null") else None
            except (TypeError, ValueError, KeyError):
                ev = None
            try:
                la = float(row["launch_angle"]) if row.get("launch_angle") not in (None, "", "null") else None
            except (TypeError, ValueError, KeyError):
                la = None
            if ev is not None and ev > 0:
                b["hard_bip"] += 1.0
                if _is_barrel(ev, la):
                    b["hard_barrels"] += 1.0
    return {pid: _metrics_from_raw(raw) for pid, raw in acc.items()}


def _ingest_rows(season: int, rows: List[Dict[str, str]]) -> None:
    by_day: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        gd = str(row.get("game_date") or "")[:10]
        if not gd:
            continue
        by_day.setdefault(gd, []).append(row)

    season_map = _ARSENAL_CUMULATIVE.setdefault(season, {})
    raw: Dict[int, Dict[str, float]] = {}
    # Seed raw from last known point so we accumulate across days.
    for pid, series in season_map.items():
        if not series:
            continue
        # Reconstruct approximate raw from last metrics (lossy but OK for rebuild-from-CSV).
        # Prefer full rebuild from CSVs in build_arsenal_index_from_cache.

    for gd in sorted(by_day):
        day_raw: Dict[int, Dict[str, float]] = {}
        for row in by_day[gd]:
            try:
                pid = int(float(row.get("pitcher") or 0))
            except (TypeError, ValueError):
                continue
            if pid <= 0:
                continue
            fam = _family(str(row.get("pitch_type") or ""))
            if fam is None:
                continue
            b = day_raw.setdefault(pid, _empty_raw())
            b["pitches"] += 1.0
            b[fam] += 1.0
            desc = str(row.get("description") or "")
            if fam == "break" and _is_whiff(desc):
                b["break_whiffs"] += 1.0
            if fam == "hard":
                try:
                    ev = (
                        float(row["launch_speed"])
                        if row.get("launch_speed") not in (None, "", "null")
                        else None
                    )
                except (TypeError, ValueError, KeyError):
                    ev = None
                try:
                    la = (
                        float(row["launch_angle"])
                        if row.get("launch_angle") not in (None, "", "null")
                        else None
                    )
                except (TypeError, ValueError, KeyError):
                    la = None
                if ev is not None and ev > 0:
                    b["hard_bip"] += 1.0
                    if _is_barrel(ev, la):
                        b["hard_barrels"] += 1.0

        for pid, inc in day_raw.items():
            tot = raw.setdefault(pid, _empty_raw())
            for k, v in inc.items():
                tot[k] = tot.get(k, 0.0) + v
            metrics = _metrics_from_raw(tot)
            series = season_map.setdefault(pid, [])
            if series and series[-1][0] == gd:
                series[-1] = (gd, metrics)
            else:
                series.append((gd, metrics))


def build_arsenal_index_from_cache(*, season: int, through: date) -> Path:
    """Full rebuild of compact arsenal as-of index from on-disk pitch CSVs."""
    season_dir = CACHE_DIR / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)
    clear_pitch_matchup_caches()
    season_map: Dict[int, List[Tuple[str, Dict[str, float]]]] = {}
    raw: Dict[int, Dict[str, float]] = {}

    paths = sorted(season_dir.glob("pitches_*.csv"))
    for path in paths:
        try:
            parts = path.stem.replace("pitches_", "").split("_")
            chunk_end = date.fromisoformat(parts[1])
        except (IndexError, ValueError):
            continue
        if chunk_end > through:
            continue
        rows = _parse_csv_text(path.read_text(encoding="utf-8", errors="replace"))
        by_day: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            gd = str(row.get("game_date") or "")[:10]
            if not gd or gd > through.isoformat():
                continue
            by_day.setdefault(gd, []).append(row)
        for gd in sorted(by_day):
            day_raw: Dict[int, Dict[str, float]] = {}
            for row in by_day[gd]:
                try:
                    pid = int(float(row.get("pitcher") or 0))
                except (TypeError, ValueError):
                    continue
                if pid <= 0:
                    continue
                fam = _family(str(row.get("pitch_type") or ""))
                if fam is None:
                    continue
                b = day_raw.setdefault(pid, _empty_raw())
                b["pitches"] += 1.0
                b[fam] += 1.0
                desc = str(row.get("description") or "")
                if fam == "break" and _is_whiff(desc):
                    b["break_whiffs"] += 1.0
                if fam == "hard":
                    try:
                        ev = (
                            float(row["launch_speed"])
                            if row.get("launch_speed") not in (None, "", "null")
                            else None
                        )
                    except (TypeError, ValueError, KeyError):
                        ev = None
                    try:
                        la = (
                            float(row["launch_angle"])
                            if row.get("launch_angle") not in (None, "", "null")
                            else None
                        )
                    except (TypeError, ValueError, KeyError):
                        la = None
                    if ev is not None and ev > 0:
                        b["hard_bip"] += 1.0
                        if _is_barrel(ev, la):
                            b["hard_barrels"] += 1.0
            for pid, inc in day_raw.items():
                tot = raw.setdefault(pid, _empty_raw())
                for k, v in inc.items():
                    tot[k] = tot.get(k, 0.0) + v
                metrics = _metrics_from_raw(tot)
                series = season_map.setdefault(pid, [])
                if series and series[-1][0] == gd:
                    series[-1] = (gd, metrics)
                else:
                    series.append((gd, metrics))

    _ARSENAL_CUMULATIVE[season] = season_map
    index_path = season_dir / "pitcher_arsenal_asof_index.json"
    compact = {
        str(pid): [{"d": d, **m} for d, m in series]
        for pid, series in season_map.items()
    }
    index_path.write_text(json.dumps(compact), encoding="utf-8")
    return index_path


def _load_arsenal_index(season: int) -> None:
    if season in _ARSENAL_CUMULATIVE and _ARSENAL_CUMULATIVE[season]:
        return
    index_path = CACHE_DIR / str(season) / "pitcher_arsenal_asof_index.json"
    if not index_path.exists():
        _ARSENAL_CUMULATIVE.setdefault(season, {})
        return
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        _ARSENAL_CUMULATIVE.setdefault(season, {})
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
                        "hard_pct": float(pt.get("hard_pct") or 0),
                        "break_pct": float(pt.get("break_pct") or 0),
                        "soft_pct": float(pt.get("soft_pct") or 0),
                        "break_whiff_pct": float(
                            pt.get("break_whiff_pct") or LEAGUE_BREAK_WHIFF
                        ),
                        "hard_barrel_pct": float(
                            pt.get("hard_barrel_pct") or LEAGUE_HARD_BARREL
                        ),
                    },
                )
            )
        season_map[int(pid_s)] = series
    _ARSENAL_CUMULATIVE[season] = season_map


def arsenal_from_stuff_shape(stuff: Dict[str, float]) -> Dict[str, float]:
    """Fallback PA-shape metrics from stuff aggregates when pitch-type index missing.

    Same as-of leakage bound as stuff; used as an *interaction* with offense
    (not a starter_quality rewrite). Prefer real pitch-type arsenal when present.
    """
    pitches = float(stuff.get("pitches") or 0.0)
    whiff = float(stuff.get("whiff_pct") or LEAGUE_BREAK_WHIFF)
    barrel = float(stuff.get("barrel_pct") or LEAGUE_HARD_BARREL)
    chase = float(stuff.get("chase_pct") or 0.28)
    break_pct = max(0.20, min(0.50, LEAGUE_BREAK_PCT + (chase - 0.28) * 0.8))
    hard_pct = max(0.35, min(0.65, 0.90 - break_pct - 0.12))
    soft_pct = max(0.05, 1.0 - hard_pct - break_pct)
    return {
        "pitches": pitches,
        "hard_pct": hard_pct,
        "break_pct": break_pct,
        "soft_pct": soft_pct,
        "break_whiff_pct": max(0.06, min(0.28, whiff * 1.18)),
        "hard_barrel_pct": max(0.02, min(0.18, barrel)),
        "source": "stuff_shape_fallback",
    }


def get_pitcher_arsenal_as_of(
    pitcher_id: int,
    *,
    as_of: date,
    season: Optional[int] = None,
    fetch_if_missing: bool = True,
    allow_stuff_fallback: bool = True,
) -> Optional[Dict[str, float]]:
    season_i = int(season or as_of.year)
    end_exclusive = as_of - timedelta(days=1)
    override = _ARSENAL_OVERRIDE.get((season_i, int(pitcher_id), as_of.isoformat()))
    if override is not None:
        return dict(override)

    if fetch_if_missing:
        try:
            ensure_statcast_pitches_through(season=season_i, through=end_exclusive)
            # Opportunistically rebuild arsenal index if CSVs exist but index missing.
            index_path = CACHE_DIR / str(season_i) / "pitcher_arsenal_asof_index.json"
            season_dir = CACHE_DIR / str(season_i)
            if (not index_path.exists()) and season_dir.exists() and any(
                season_dir.glob("pitches_*.csv")
            ):
                build_arsenal_index_from_cache(season=season_i, through=end_exclusive)
        except Exception:
            pass

    _load_arsenal_index(season_i)
    series = (_ARSENAL_CUMULATIVE.get(season_i) or {}).get(int(pitcher_id)) or []
    cutoff = end_exclusive.isoformat()
    chosen: Optional[Dict[str, float]] = None
    for d, metrics in series:
        if d <= cutoff:
            chosen = metrics
        else:
            break
    if chosen is not None and float(chosen.get("pitches") or 0) >= MIN_PITCHES_ARSENAL:
        out = dict(chosen)
        out["as_of_pitches_through"] = cutoff
        out["source"] = "pitch_type_arsenal"
        return out

    if allow_stuff_fallback:
        try:
            from .mlb_statcast_stuff import get_pitcher_stuff_as_of

            stuff = get_pitcher_stuff_as_of(
                int(pitcher_id),
                as_of=as_of,
                season=season_i,
                fetch_if_missing=False,
            )
            if stuff is not None:
                shaped = arsenal_from_stuff_shape(stuff)
                shaped["as_of_pitches_through"] = cutoff
                return shaped
        except Exception:
            pass
    return None


def pitch_level_matchup_mul(
    *,
    offense_split: float,
    recent_form: float,
    arsenal: Optional[Dict[str, float]],
    opp_firmness: float,
) -> float:
    """Bounded PA-shape mul from pitcher arsenal × offense contact/power proxy."""
    if not PITCH_MATCHUP_ENABLED or not arsenal:
        return 1.0
    contact = 0.55 * (float(offense_split) - 1.0) + 0.45 * (float(recent_form) - 1.0)
    break_whiff = float(arsenal.get("break_whiff_pct") or LEAGUE_BREAK_WHIFF)
    hard_barrel = float(arsenal.get("hard_barrel_pct") or LEAGUE_HARD_BARREL)
    break_pct = float(arsenal.get("break_pct") or LEAGUE_BREAK_PCT)

    # Weak contact crushed by high-whiff break; power feasts when hard stuff barrels.
    weak = max(0.0, 0.03 - contact)
    power = max(0.0, contact)
    edge = (
        -0.10 * (break_whiff - LEAGUE_BREAK_WHIFF) / 0.04 * weak
        + 0.08 * (hard_barrel - LEAGUE_HARD_BARREL) / 0.03 * power
        + 0.03 * (break_pct - LEAGUE_BREAK_PCT) * contact
    )
    firm = max(0.35, min(1.0, float(opp_firmness)))
    raw = 1.0 + edge * (0.45 + 0.55 * firm)
    return max(0.97, min(1.03, raw))
