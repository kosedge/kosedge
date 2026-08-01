"""Batter–pitcher pitch-type arsenal PA matchup (true mix), not SP quality.

Distinct from:
  - matchup_mul (team split × season K/BB/GB)
  - starter_quality stuff_proxy / FIP / era_whip (run-allowed factor)

Uses as-of Statcast pitch-type mix (FF/SI/SL/CH/CU/…) × batter-family
contact/whiff. Flag default OFF. Stuff-shape fallback default OFF for densify.
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
    _is_swing,
    _is_whiff,
    _parse_csv_text,
    ensure_statcast_pitches_through,
)

MIN_PITCHES_ARSENAL = 180
MIN_PITCHES_BATTER_FAMILY = 400

# League anchors (approx MLB means) for z-ish interaction.
LEAGUE_BREAK_WHIFF = 0.135
LEAGUE_HARD_WHIFF = 0.095
LEAGUE_SOFT_WHIFF = 0.145
LEAGUE_HARD_BARREL = 0.085
LEAGUE_BREAK_PCT = 0.34
LEAGUE_FF_SI_PCT = 0.52
LEAGUE_BATTER_HARD_WHIFF = 0.095
LEAGUE_BATTER_BREAK_WHIFF = 0.135
LEAGUE_BATTER_SOFT_WHIFF = 0.145

HARD_TYPES = frozenset({"FF", "SI", "FC", "FA"})
BREAK_TYPES = frozenset({"SL", "CU", "KC", "SV", "ST", "CS"})
SOFT_TYPES = frozenset({"CH", "FS", "FO", "SC", "KN"})
# Individual pitch-type usage tracked in the arsenal vector.
TRACKED_TYPES = ("FF", "SI", "FC", "SL", "CH", "CU", "FS", "ST", "KC")

# Statcast CSV abbrs ↔ common DB / Odds abbrs.
_TEAM_ABBR_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ARI": ("ARI", "AZ"),
    "AZ": ("AZ", "ARI"),
    "CHW": ("CHW", "CWS"),
    "CWS": ("CWS", "CHW"),
    "OAK": ("OAK", "ATH"),
    "ATH": ("ATH", "OAK"),
    "WSH": ("WSH", "WAS"),
    "WAS": ("WAS", "WSH"),
    "SD": ("SD", "SDP"),
    "SDP": ("SDP", "SD"),
    "SF": ("SF", "SFG"),
    "SFG": ("SFG", "SF"),
    "TB": ("TB", "TBR"),
    "TBR": ("TBR", "TB"),
}

_ARSENAL_CUMULATIVE: Dict[int, Dict[int, List[Tuple[str, Dict[str, float]]]]] = {}
_BATTER_FAMILY_CUMULATIVE: Dict[int, Dict[str, List[Tuple[str, Dict[str, float]]]]] = {}
_ARSENAL_OVERRIDE: Dict[Tuple[int, int, str], Dict[str, float]] = {}
_BATTER_FAMILY_OVERRIDE: Dict[Tuple[int, str, str], Dict[str, float]] = {}

PITCH_MATCHUP_ENABLED = (
    str(os.getenv("MLB_PITCH_MATCHUP_ENABLED") or "false").strip().lower()
    in {"1", "true", "yes", "on"}
)
# Default OFF — prior densify M1 was contaminated by stuff-shape when pitch_type
# failed to parse (UTF-8 BOM). True arsenal path must not silently fall back.
PITCH_MATCHUP_STUFF_FALLBACK = (
    str(os.getenv("MLB_PITCH_MATCHUP_STUFF_FALLBACK") or "false").strip().lower()
    in {"1", "true", "yes", "on"}
)


def apply_pitch_matchup_flag(enabled: Optional[bool] = None) -> bool:
    global PITCH_MATCHUP_ENABLED
    if enabled is not None:
        PITCH_MATCHUP_ENABLED = bool(enabled)
    return bool(PITCH_MATCHUP_ENABLED)


def get_pitch_matchup_enabled() -> bool:
    return bool(PITCH_MATCHUP_ENABLED)


def apply_pitch_matchup_stuff_fallback(enabled: Optional[bool] = None) -> bool:
    global PITCH_MATCHUP_STUFF_FALLBACK
    if enabled is not None:
        PITCH_MATCHUP_STUFF_FALLBACK = bool(enabled)
    return bool(PITCH_MATCHUP_STUFF_FALLBACK)


def get_pitch_matchup_stuff_fallback() -> bool:
    return bool(PITCH_MATCHUP_STUFF_FALLBACK)


def reset_pitch_matchup_from_env() -> bool:
    apply_pitch_matchup_stuff_fallback(
        str(os.getenv("MLB_PITCH_MATCHUP_STUFF_FALLBACK") or "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    return apply_pitch_matchup_flag(
        str(os.getenv("MLB_PITCH_MATCHUP_ENABLED") or "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )


def clear_pitch_matchup_caches() -> None:
    _ARSENAL_CUMULATIVE.clear()
    _BATTER_FAMILY_CUMULATIVE.clear()
    _ARSENAL_OVERRIDE.clear()
    _BATTER_FAMILY_OVERRIDE.clear()


def set_arsenal_metrics_override(
    *,
    season: int,
    pitcher_id: int,
    as_of: date,
    metrics: Dict[str, float],
) -> None:
    _ARSENAL_OVERRIDE[(int(season), int(pitcher_id), as_of.isoformat())] = dict(metrics)


def set_batter_family_override(
    *,
    season: int,
    team_abbr: str,
    as_of: date,
    metrics: Dict[str, float],
) -> None:
    key = (int(season), str(team_abbr or "").upper(), as_of.isoformat())
    _BATTER_FAMILY_OVERRIDE[key] = dict(metrics)


def _family(pitch_type: str) -> Optional[str]:
    pt = (pitch_type or "").strip().upper()
    if pt in HARD_TYPES:
        return "hard"
    if pt in BREAK_TYPES:
        return "break"
    if pt in SOFT_TYPES:
        return "soft"
    return None


def _batting_team_abbr(row: Dict[str, Any]) -> Optional[str]:
    topbot = str(row.get("inning_topbot") or "").strip().lower()
    if topbot.startswith("top"):
        abbr = str(row.get("away_team") or "").strip().upper()
    elif topbot.startswith("bot"):
        abbr = str(row.get("home_team") or "").strip().upper()
    else:
        return None
    return abbr or None


def _empty_arsenal_raw() -> Dict[str, float]:
    raw = {
        "pitches": 0.0,
        "hard": 0.0,
        "break": 0.0,
        "soft": 0.0,
        "hard_whiffs": 0.0,
        "break_whiffs": 0.0,
        "soft_whiffs": 0.0,
        "hard_bip": 0.0,
        "hard_barrels": 0.0,
        "other": 0.0,
    }
    for pt in TRACKED_TYPES:
        raw[f"pt_{pt}"] = 0.0
        raw[f"whiff_{pt}"] = 0.0
    return raw


def _empty_batter_raw() -> Dict[str, float]:
    return {
        "pitches": 0.0,
        "hard": 0.0,
        "break": 0.0,
        "soft": 0.0,
        "hard_swings": 0.0,
        "break_swings": 0.0,
        "soft_swings": 0.0,
        "hard_whiffs": 0.0,
        "break_whiffs": 0.0,
        "soft_whiffs": 0.0,
        "hard_bip": 0.0,
        "hard_barrels": 0.0,
    }


def _arsenal_metrics_from_raw(raw: Dict[str, float]) -> Dict[str, float]:
    pitches = float(raw.get("pitches") or 0.0)
    if pitches <= 0:
        out = {
            "pitches": 0.0,
            "hard_pct": 0.0,
            "break_pct": 0.0,
            "soft_pct": 0.0,
            "other_pct": 0.0,
            "ff_pct": 0.0,
            "si_pct": 0.0,
            "fc_pct": 0.0,
            "sl_pct": 0.0,
            "ch_pct": 0.0,
            "cu_pct": 0.0,
            "fs_pct": 0.0,
            "st_pct": 0.0,
            "kc_pct": 0.0,
            "hard_whiff_pct": LEAGUE_HARD_WHIFF,
            "break_whiff_pct": LEAGUE_BREAK_WHIFF,
            "soft_whiff_pct": LEAGUE_SOFT_WHIFF,
            "hard_barrel_pct": LEAGUE_HARD_BARREL,
        }
        return out
    hard = float(raw.get("hard") or 0.0)
    brk = float(raw.get("break") or 0.0)
    soft = float(raw.get("soft") or 0.0)
    hard_bip = float(raw.get("hard_bip") or 0.0)
    out: Dict[str, float] = {
        "pitches": pitches,
        "hard_pct": hard / pitches,
        "break_pct": brk / pitches,
        "soft_pct": soft / pitches,
        "other_pct": float(raw.get("other") or 0.0) / pitches,
        "ff_pct": float(raw.get("pt_FF") or 0.0) / pitches,
        "si_pct": float(raw.get("pt_SI") or 0.0) / pitches,
        "fc_pct": float(raw.get("pt_FC") or 0.0) / pitches,
        "sl_pct": float(raw.get("pt_SL") or 0.0) / pitches,
        "ch_pct": float(raw.get("pt_CH") or 0.0) / pitches,
        "cu_pct": float(raw.get("pt_CU") or 0.0) / pitches,
        "fs_pct": float(raw.get("pt_FS") or 0.0) / pitches,
        "st_pct": float(raw.get("pt_ST") or 0.0) / pitches,
        "kc_pct": float(raw.get("pt_KC") or 0.0) / pitches,
        "hard_whiff_pct": (
            float(raw.get("hard_whiffs") or 0.0) / hard if hard > 0 else LEAGUE_HARD_WHIFF
        ),
        "break_whiff_pct": (
            float(raw.get("break_whiffs") or 0.0) / brk if brk > 0 else LEAGUE_BREAK_WHIFF
        ),
        "soft_whiff_pct": (
            float(raw.get("soft_whiffs") or 0.0) / soft if soft > 0 else LEAGUE_SOFT_WHIFF
        ),
        "hard_barrel_pct": (
            float(raw.get("hard_barrels") or 0.0) / hard_bip
            if hard_bip > 0
            else LEAGUE_HARD_BARREL
        ),
    }
    return out


def _batter_metrics_from_raw(raw: Dict[str, float]) -> Dict[str, float]:
    pitches = float(raw.get("pitches") or 0.0)
    hard = float(raw.get("hard") or 0.0)
    brk = float(raw.get("break") or 0.0)
    soft = float(raw.get("soft") or 0.0)
    hard_bip = float(raw.get("hard_bip") or 0.0)

    def _whiff(family: str, league: float) -> float:
        n = float(raw.get(family) or 0.0)
        if n <= 0:
            return league
        return float(raw.get(f"{family}_whiffs") or 0.0) / n

    def _contact(family: str) -> float:
        swings = float(raw.get(f"{family}_swings") or 0.0)
        if swings <= 0:
            return 0.78
        whiffs = float(raw.get(f"{family}_whiffs") or 0.0)
        return max(0.0, min(1.0, (swings - whiffs) / swings))

    return {
        "pitches": pitches,
        "hard_pct_faced": hard / pitches if pitches > 0 else 0.0,
        "break_pct_faced": brk / pitches if pitches > 0 else 0.0,
        "soft_pct_faced": soft / pitches if pitches > 0 else 0.0,
        "hard_whiff_pct": _whiff("hard", LEAGUE_BATTER_HARD_WHIFF),
        "break_whiff_pct": _whiff("break", LEAGUE_BATTER_BREAK_WHIFF),
        "soft_whiff_pct": _whiff("soft", LEAGUE_BATTER_SOFT_WHIFF),
        "hard_contact_pct": _contact("hard"),
        "break_contact_pct": _contact("break"),
        "soft_contact_pct": _contact("soft"),
        "hard_barrel_pct": (
            float(raw.get("hard_barrels") or 0.0) / hard_bip
            if hard_bip > 0
            else LEAGUE_HARD_BARREL
        ),
    }


def _accumulate_arsenal_row(raw: Dict[str, float], row: Dict[str, Any]) -> None:
    pt = str(row.get("pitch_type") or "").strip().upper()
    fam = _family(pt)
    if fam is None and not pt:
        return
    raw["pitches"] += 1.0
    if fam is None:
        raw["other"] += 1.0
        return
    raw[fam] += 1.0
    if pt in TRACKED_TYPES:
        raw[f"pt_{pt}"] += 1.0
    desc = str(row.get("description") or "")
    if _is_whiff(desc):
        raw[f"{fam}_whiffs"] += 1.0
        if pt in TRACKED_TYPES:
            raw[f"whiff_{pt}"] += 1.0
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
            raw["hard_bip"] += 1.0
            if _is_barrel(ev, la):
                raw["hard_barrels"] += 1.0


def _accumulate_batter_row(raw: Dict[str, float], row: Dict[str, Any]) -> None:
    fam = _family(str(row.get("pitch_type") or ""))
    if fam is None:
        return
    raw["pitches"] += 1.0
    raw[fam] += 1.0
    desc = str(row.get("description") or "")
    if _is_swing(desc):
        raw[f"{fam}_swings"] += 1.0
    if _is_whiff(desc):
        raw[f"{fam}_whiffs"] += 1.0
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
            raw["hard_bip"] += 1.0
            if _is_barrel(ev, la):
                raw["hard_barrels"] += 1.0


def aggregate_arsenal_rows(rows: Iterable[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    acc: Dict[int, Dict[str, float]] = {}
    for row in rows:
        try:
            pitcher_id = int(float(row.get("pitcher") or 0))
        except (TypeError, ValueError):
            continue
        if pitcher_id <= 0:
            continue
        b = acc.setdefault(pitcher_id, _empty_arsenal_raw())
        _accumulate_arsenal_row(b, row)
    return {pid: _arsenal_metrics_from_raw(raw) for pid, raw in acc.items()}


def build_true_arsenal_indexes_from_cache(*, season: int, through: date) -> Dict[str, Path]:
    """Full rebuild of pitcher arsenal + team batter-family as-of indexes from CSVs."""
    season_dir = CACHE_DIR / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)
    clear_pitch_matchup_caches()

    arsenal_map: Dict[int, List[Tuple[str, Dict[str, float]]]] = {}
    batter_map: Dict[str, List[Tuple[str, Dict[str, float]]]] = {}
    arsenal_raw: Dict[int, Dict[str, float]] = {}
    batter_raw: Dict[str, Dict[str, float]] = {}

    paths = sorted(season_dir.glob("pitches_*.csv"))
    # Also scan sibling repo cache if CACHE_DIR has index-only (Railway image).
    if not paths:
        here = Path(__file__).resolve()
        alt = here.parents[4] / "data" / "mlb" / "statcast_cache" / str(season)
        if alt.exists():
            paths = sorted(alt.glob("pitches_*.csv"))

    for path in paths:
        try:
            parts = path.stem.replace("pitches_", "").split("_")
            chunk_end = date.fromisoformat(parts[1])
        except (IndexError, ValueError):
            continue
        if chunk_end > through:
            continue
        rows = _parse_csv_text(path.read_text(encoding="utf-8-sig", errors="replace"))
        by_day: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            gd = str(row.get("game_date") or "")[:10]
            if not gd or gd > through.isoformat():
                continue
            by_day.setdefault(gd, []).append(row)
        for gd in sorted(by_day):
            day_arsenal: Dict[int, Dict[str, float]] = {}
            day_batter: Dict[str, Dict[str, float]] = {}
            for row in by_day[gd]:
                try:
                    pid = int(float(row.get("pitcher") or 0))
                except (TypeError, ValueError):
                    pid = 0
                if pid > 0:
                    b = day_arsenal.setdefault(pid, _empty_arsenal_raw())
                    _accumulate_arsenal_row(b, row)
                team = _batting_team_abbr(row)
                if team:
                    tb = day_batter.setdefault(team, _empty_batter_raw())
                    _accumulate_batter_row(tb, row)

            for pid, inc in day_arsenal.items():
                tot = arsenal_raw.setdefault(pid, _empty_arsenal_raw())
                for k, v in inc.items():
                    tot[k] = tot.get(k, 0.0) + v
                metrics = _arsenal_metrics_from_raw(tot)
                series = arsenal_map.setdefault(pid, [])
                if series and series[-1][0] == gd:
                    series[-1] = (gd, metrics)
                else:
                    series.append((gd, metrics))

            for team, inc in day_batter.items():
                tot = batter_raw.setdefault(team, _empty_batter_raw())
                for k, v in inc.items():
                    tot[k] = tot.get(k, 0.0) + v
                metrics = _batter_metrics_from_raw(tot)
                series = batter_map.setdefault(team, [])
                if series and series[-1][0] == gd:
                    series[-1] = (gd, metrics)
                else:
                    series.append((gd, metrics))

    _ARSENAL_CUMULATIVE[season] = arsenal_map
    _BATTER_FAMILY_CUMULATIVE[season] = batter_map

    arsenal_path = season_dir / "pitcher_arsenal_asof_index.json"
    batter_path = season_dir / "team_batter_family_asof_index.json"
    arsenal_path.write_text(
        json.dumps(
            {
                str(pid): [{"d": d, **m} for d, m in series]
                for pid, series in arsenal_map.items()
            }
        ),
        encoding="utf-8",
    )
    batter_path.write_text(
        json.dumps(
            {
                team: [{"d": d, **m} for d, m in series]
                for team, series in batter_map.items()
            }
        ),
        encoding="utf-8",
    )
    # Mirror into service image path when building from repo-root CSVs.
    here = Path(__file__).resolve()
    service_dir = here.parents[2] / "data" / "mlb" / "statcast_cache" / str(season)
    if service_dir.resolve() != season_dir.resolve():
        service_dir.mkdir(parents=True, exist_ok=True)
        (service_dir / arsenal_path.name).write_text(
            arsenal_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (service_dir / batter_path.name).write_text(
            batter_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return {"arsenal": arsenal_path, "batter_family": batter_path}


# Back-compat alias used by older call sites / tests.
def build_arsenal_index_from_cache(*, season: int, through: date) -> Path:
    return build_true_arsenal_indexes_from_cache(season=season, through=through)["arsenal"]


def _load_arsenal_index(season: int) -> None:
    if season in _ARSENAL_CUMULATIVE and _ARSENAL_CUMULATIVE[season]:
        return
    index_path = CACHE_DIR / str(season) / "pitcher_arsenal_asof_index.json"
    if not index_path.exists():
        # Service image may hold indexes even when CACHE_DIR resolved to repo CSVs.
        alt = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "mlb"
            / "statcast_cache"
            / str(season)
            / "pitcher_arsenal_asof_index.json"
        )
        index_path = alt if alt.exists() else index_path
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
            metrics = {
                "pitches": float(pt.get("pitches") or 0),
                "hard_pct": float(pt.get("hard_pct") or 0),
                "break_pct": float(pt.get("break_pct") or 0),
                "soft_pct": float(pt.get("soft_pct") or 0),
                "other_pct": float(pt.get("other_pct") or 0),
                "ff_pct": float(pt.get("ff_pct") or 0),
                "si_pct": float(pt.get("si_pct") or 0),
                "fc_pct": float(pt.get("fc_pct") or 0),
                "sl_pct": float(pt.get("sl_pct") or 0),
                "ch_pct": float(pt.get("ch_pct") or 0),
                "cu_pct": float(pt.get("cu_pct") or 0),
                "fs_pct": float(pt.get("fs_pct") or 0),
                "st_pct": float(pt.get("st_pct") or 0),
                "kc_pct": float(pt.get("kc_pct") or 0),
                "hard_whiff_pct": float(pt.get("hard_whiff_pct") or LEAGUE_HARD_WHIFF),
                "break_whiff_pct": float(pt.get("break_whiff_pct") or LEAGUE_BREAK_WHIFF),
                "soft_whiff_pct": float(pt.get("soft_whiff_pct") or LEAGUE_SOFT_WHIFF),
                "hard_barrel_pct": float(pt.get("hard_barrel_pct") or LEAGUE_HARD_BARREL),
            }
            series.append((d, metrics))
        season_map[int(pid_s)] = series
    _ARSENAL_CUMULATIVE[season] = season_map


def _load_batter_family_index(season: int) -> None:
    if season in _BATTER_FAMILY_CUMULATIVE and _BATTER_FAMILY_CUMULATIVE[season]:
        return
    index_path = CACHE_DIR / str(season) / "team_batter_family_asof_index.json"
    if not index_path.exists():
        alt = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "mlb"
            / "statcast_cache"
            / str(season)
            / "team_batter_family_asof_index.json"
        )
        index_path = alt if alt.exists() else index_path
    if not index_path.exists():
        _BATTER_FAMILY_CUMULATIVE.setdefault(season, {})
        return
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        _BATTER_FAMILY_CUMULATIVE.setdefault(season, {})
        return
    season_map: Dict[str, List[Tuple[str, Dict[str, float]]]] = {}
    for team, points in (payload or {}).items():
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
                        "hard_pct_faced": float(pt.get("hard_pct_faced") or 0),
                        "break_pct_faced": float(pt.get("break_pct_faced") or 0),
                        "soft_pct_faced": float(pt.get("soft_pct_faced") or 0),
                        "hard_whiff_pct": float(
                            pt.get("hard_whiff_pct") or LEAGUE_BATTER_HARD_WHIFF
                        ),
                        "break_whiff_pct": float(
                            pt.get("break_whiff_pct") or LEAGUE_BATTER_BREAK_WHIFF
                        ),
                        "soft_whiff_pct": float(
                            pt.get("soft_whiff_pct") or LEAGUE_BATTER_SOFT_WHIFF
                        ),
                        "hard_contact_pct": float(pt.get("hard_contact_pct") or 0.78),
                        "break_contact_pct": float(pt.get("break_contact_pct") or 0.72),
                        "soft_contact_pct": float(pt.get("soft_contact_pct") or 0.70),
                        "hard_barrel_pct": float(
                            pt.get("hard_barrel_pct") or LEAGUE_HARD_BARREL
                        ),
                    },
                )
            )
        season_map[str(team).upper()] = series
    _BATTER_FAMILY_CUMULATIVE[season] = season_map


def arsenal_from_stuff_shape(stuff: Dict[str, float]) -> Dict[str, float]:
    """Legacy fallback PA-shape from stuff aggregates (disabled by default)."""
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
        "other_pct": 0.0,
        "ff_pct": hard_pct * 0.55,
        "si_pct": hard_pct * 0.30,
        "fc_pct": hard_pct * 0.15,
        "sl_pct": break_pct * 0.55,
        "ch_pct": soft_pct * 0.70,
        "cu_pct": break_pct * 0.25,
        "fs_pct": soft_pct * 0.30,
        "st_pct": break_pct * 0.15,
        "kc_pct": break_pct * 0.05,
        "hard_whiff_pct": max(0.05, min(0.20, whiff * 0.85)),
        "break_whiff_pct": max(0.06, min(0.28, whiff * 1.18)),
        "soft_whiff_pct": max(0.08, min(0.28, whiff * 1.10)),
        "hard_barrel_pct": max(0.02, min(0.18, barrel)),
        "source": "stuff_shape_fallback",
    }


def get_pitcher_arsenal_as_of(
    pitcher_id: int,
    *,
    as_of: date,
    season: Optional[int] = None,
    fetch_if_missing: bool = True,
    allow_stuff_fallback: Optional[bool] = None,
) -> Optional[Dict[str, float]]:
    season_i = int(season or as_of.year)
    end_exclusive = as_of - timedelta(days=1)
    override = _ARSENAL_OVERRIDE.get((season_i, int(pitcher_id), as_of.isoformat()))
    if override is not None:
        return dict(override)

    use_fallback = (
        bool(PITCH_MATCHUP_STUFF_FALLBACK)
        if allow_stuff_fallback is None
        else bool(allow_stuff_fallback)
    )

    if fetch_if_missing:
        try:
            ensure_statcast_pitches_through(season=season_i, through=end_exclusive)
            index_path = CACHE_DIR / str(season_i) / "pitcher_arsenal_asof_index.json"
            season_dir = CACHE_DIR / str(season_i)
            if (not index_path.exists()) and season_dir.exists() and any(
                season_dir.glob("pitches_*.csv")
            ):
                build_true_arsenal_indexes_from_cache(
                    season=season_i, through=end_exclusive
                )
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

    if use_fallback:
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


def _team_abbr_candidates(team_abbr: str) -> Tuple[str, ...]:
    abbr = str(team_abbr or "").strip().upper()
    if not abbr:
        return ()
    return _TEAM_ABBR_ALIASES.get(abbr, (abbr,))


def get_team_batter_family_as_of(
    team_abbr: str,
    *,
    as_of: date,
    season: Optional[int] = None,
    fetch_if_missing: bool = True,
) -> Optional[Dict[str, float]]:
    candidates = _team_abbr_candidates(team_abbr)
    if not candidates:
        return None
    abbr = candidates[0]
    season_i = int(season or as_of.year)
    end_exclusive = as_of - timedelta(days=1)
    for cand in candidates:
        override = _BATTER_FAMILY_OVERRIDE.get((season_i, cand, as_of.isoformat()))
        if override is not None:
            return dict(override)

    if fetch_if_missing:
        try:
            ensure_statcast_pitches_through(season=season_i, through=end_exclusive)
            index_path = CACHE_DIR / str(season_i) / "team_batter_family_asof_index.json"
            season_dir = CACHE_DIR / str(season_i)
            if (not index_path.exists()) and season_dir.exists() and any(
                season_dir.glob("pitches_*.csv")
            ):
                build_true_arsenal_indexes_from_cache(
                    season=season_i, through=end_exclusive
                )
        except Exception:
            pass

    _load_batter_family_index(season_i)
    season_map = _BATTER_FAMILY_CUMULATIVE.get(season_i) or {}
    series: List[Tuple[str, Dict[str, float]]] = []
    resolved = abbr
    for cand in candidates:
        series = season_map.get(cand) or []
        if series:
            resolved = cand
            break
    cutoff = end_exclusive.isoformat()
    chosen: Optional[Dict[str, float]] = None
    for d, metrics in series:
        if d <= cutoff:
            chosen = metrics
        else:
            break
    if chosen is None or float(chosen.get("pitches") or 0) < MIN_PITCHES_BATTER_FAMILY:
        return None
    out = dict(chosen)
    out["as_of_pitches_through"] = cutoff
    out["source"] = "team_batter_family"
    out["team"] = resolved
    return out


def pitch_level_matchup_mul(
    *,
    offense_split: float,
    recent_form: float,
    arsenal: Optional[Dict[str, float]],
    opp_firmness: float,
    batter_family: Optional[Dict[str, float]] = None,
) -> float:
    """Bounded PA-shape mul from true arsenal × batter-family (or split proxy)."""
    if not PITCH_MATCHUP_ENABLED or not arsenal:
        return 1.0

    firm = max(0.35, min(1.0, float(opp_firmness)))
    hard_pct = float(arsenal.get("hard_pct") or 0.0)
    break_pct = float(arsenal.get("break_pct") or LEAGUE_BREAK_PCT)
    soft_pct = float(arsenal.get("soft_pct") or 0.0)
    ff_si = float(arsenal.get("ff_pct") or 0.0) + float(arsenal.get("si_pct") or 0.0)
    p_hard_whiff = float(arsenal.get("hard_whiff_pct") or LEAGUE_HARD_WHIFF)
    p_break_whiff = float(arsenal.get("break_whiff_pct") or LEAGUE_BREAK_WHIFF)
    p_soft_whiff = float(arsenal.get("soft_whiff_pct") or LEAGUE_SOFT_WHIFF)
    p_hard_barrel = float(arsenal.get("hard_barrel_pct") or LEAGUE_HARD_BARREL)

    if batter_family and float(batter_family.get("pitches") or 0) > 0:
        b_hard_whiff = float(
            batter_family.get("hard_whiff_pct") or LEAGUE_BATTER_HARD_WHIFF
        )
        b_break_whiff = float(
            batter_family.get("break_whiff_pct") or LEAGUE_BATTER_BREAK_WHIFF
        )
        b_soft_whiff = float(
            batter_family.get("soft_whiff_pct") or LEAGUE_BATTER_SOFT_WHIFF
        )
        b_hard_contact = float(batter_family.get("hard_contact_pct") or 0.78)
        b_hard_barrel = float(
            batter_family.get("hard_barrel_pct") or LEAGUE_HARD_BARREL
        )

        # Whiff pressure: pitcher throws family X with elevated whiff AND batter
        # also whiffs elevated vs X → suppress offense.
        whiff_pressure = (
            hard_pct
            * ((p_hard_whiff - LEAGUE_HARD_WHIFF) / 0.03)
            * ((b_hard_whiff - LEAGUE_BATTER_HARD_WHIFF) / 0.03)
            + break_pct
            * ((p_break_whiff - LEAGUE_BREAK_WHIFF) / 0.04)
            * ((b_break_whiff - LEAGUE_BATTER_BREAK_WHIFF) / 0.04)
            + soft_pct
            * ((p_soft_whiff - LEAGUE_SOFT_WHIFF) / 0.04)
            * ((b_soft_whiff - LEAGUE_BATTER_SOFT_WHIFF) / 0.04)
        )
        # Meatball / contact feast: FF/SI-heavy arsenals that barrel vs contact bats.
        meat = (
            hard_pct
            * ((p_hard_barrel - LEAGUE_HARD_BARREL) / 0.03)
            * ((b_hard_contact - 0.78) / 0.06 + (b_hard_barrel - LEAGUE_HARD_BARREL) / 0.03)
        )
        mix_shape = ((ff_si - LEAGUE_FF_SI_PCT) / 0.10) * (
            (b_hard_contact - 0.78) / 0.06
        )
        edge = -0.012 * whiff_pressure + 0.010 * meat + 0.006 * mix_shape
        source_scale = 1.0
    else:
        # Thin / missing batter-family: degrade to offense split/form proxy only
        # (still uses true pitcher arsenal rates — not stuff-shape).
        contact = 0.55 * (float(offense_split) - 1.0) + 0.45 * (float(recent_form) - 1.0)
        weak = max(0.0, 0.03 - contact)
        power = max(0.0, contact)
        edge = (
            -0.10 * (p_break_whiff - LEAGUE_BREAK_WHIFF) / 0.04 * weak
            + 0.08 * (p_hard_barrel - LEAGUE_HARD_BARREL) / 0.03 * power
            + 0.03 * (break_pct - LEAGUE_BREAK_PCT) * contact
            + 0.02 * (ff_si - LEAGUE_FF_SI_PCT) * contact
        )
        source_scale = 0.85

    raw = 1.0 + edge * (0.45 + 0.55 * firm) * source_scale
    return max(0.97, min(1.03, raw))
