#!/usr/bin/env python3
"""Record/HFA baseline method — request v3.1 §2 (35cbb56e).

Same method as v6 scorer inputs/record_baseline_le2023.csv (502110cf).
Pre-game information only. Ties do not increment W or L.
Hardcoded -3.0 / 45.0 is not this method.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

HFA = 1.05
BASE_TOTAL = 45.3
MARGIN_WEIGHT = 16.0
TOTAL_WEIGHT = 10.5
MAX_MARGIN = 6.5
MAX_TOTAL = 5.0
ALIASES = {
    "LAR": "LA",
    "STL": "LA",
    "SD": "LAC",
    "OAK": "LV",
    "WSH": "WAS",
    "JAC": "JAX",
}


def alias(team: str) -> str:
    raw = (team or "").strip().upper()
    return ALIASES.get(raw, raw)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def team_strength_from_record(wins: int, losses: int) -> Tuple[float, float]:
    games = max(1.0, float(max(0, wins) + max(0, losses)))
    win_pct = float(max(0, wins)) / games if (wins + losses) else 0.0
    offense = clamp(0.90 + (0.22 * win_pct), 0.82, 1.18)
    defense = clamp(0.92 + (0.20 * win_pct), 0.82, 1.20)
    return offense, defense


def decompose_record_hfa(off_home: float, def_home: float, off_away: float, def_away: float) -> Tuple[float, float]:
    off_def_home = clamp((off_home / max(0.75, def_away)) - 1.0, -0.25, 0.25)
    off_def_away = clamp((off_away / max(0.75, def_home)) - 1.0, -0.25, 0.25)
    margin = clamp((off_def_home - off_def_away) * MARGIN_WEIGHT, -MAX_MARGIN, MAX_MARGIN) + HFA
    total = BASE_TOTAL + clamp((off_def_home + off_def_away) * TOTAL_WEIGHT, -MAX_TOTAL, MAX_TOTAL)
    return margin, total


def record_spread_total(wins_home: int, losses_home: int, wins_away: int, losses_away: int) -> Tuple[float, float]:
    off_h, def_h = team_strength_from_record(wins_home, losses_home)
    off_a, def_a = team_strength_from_record(wins_away, losses_away)
    margin, total = decompose_record_hfa(off_h, def_h, off_a, def_a)
    record_spread = round(-margin, 4)
    record_total = round(total, 4)
    return record_spread, record_total


def build_record_book(schedule: Sequence[Dict[str, Any]]) -> Dict[Tuple[int, int, str, str], Dict[str, float]]:
    """Prior-week W-L only. Same-week results do not enter. Ties ignored."""
    wl: Dict[Tuple[int, str], List[int]] = {}
    out: Dict[Tuple[int, int, str, str], Dict[str, float]] = {}
    by_sw: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for game in schedule:
        season = int(game["season"])
        week = int(game["week"])
        rec = dict(game)
        rec["home"] = alias(str(game.get("home") or ""))
        rec["away"] = alias(str(game.get("away") or ""))
        by_sw.setdefault((season, week), []).append(rec)
    for season, week in sorted(by_sw):
        for game in by_sw[(season, week)]:
            home, away = game["home"], game["away"]
            hw, hl = wl.setdefault((season, home), [0, 0])
            aw, al = wl.setdefault((season, away), [0, 0])
            record_spread, record_total = record_spread_total(hw, hl, aw, al)
            out[(season, week, home, away)] = {
                "record_spread": record_spread,
                "record_total": record_total,
                "baseline_margin": -record_spread,
                "baseline_total": record_total,
            }
        for game in by_sw[(season, week)]:
            am = game.get("actual_margin")
            if am is None:
                hs, aws = game.get("home_score"), game.get("away_score")
                if hs is None or aws is None or str(hs).strip() == "" or str(aws).strip() == "":
                    continue
                am = float(hs) - float(aws)
            am = float(am)
            if am > 0:
                wl[(season, game["home"])][0] += 1
                wl[(season, game["away"])][1] += 1
            elif am < 0:
                wl[(season, game["away"])][0] += 1
                wl[(season, game["home"])][1] += 1
    return out


def lookup_baseline(
    book: MutableMapping[Tuple[int, int, str, str], Dict[str, float]],
    season: int,
    week: int,
    home: str,
    away: str,
) -> Optional[Tuple[float, float]]:
    rec = book.get((int(season), int(week), alias(home), alias(away)))
    if not rec:
        return None
    return float(rec["baseline_margin"]), float(rec["baseline_total"])


def week1_identity() -> Tuple[float, float]:
    spread, total = record_spread_total(0, 0, 0, 0)
    return -spread, total
