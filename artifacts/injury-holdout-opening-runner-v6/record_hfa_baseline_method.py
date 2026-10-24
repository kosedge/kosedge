#!/usr/bin/env python3
"""Record/HFA baseline method — request v3.1 §2 (35cbb56e). B-9 ROUND_HALF_UP.

Same method as v6 scorer inputs/record_baseline_le2023.csv (502110cf).
Pre-game information only. Ties do not increment W or L.
Hardcoded -3.0 / 45.0 is not this method.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, MutableMapping, Optional, Sequence, Tuple

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


def clamp(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return max(lo, min(hi, value))


def round4(value: Decimal) -> float:
    """B-9: Decimal ROUND_HALF_UP to 4 decimals so 45.35625 → 45.3563."""
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def team_strength_from_record(wins: int, losses: int) -> Tuple[Decimal, Decimal]:
    w = Decimal(max(0, wins))
    l = Decimal(max(0, losses))
    games = w + l
    win_pct = (w / games) if games else Decimal("0")
    offense = clamp(Decimal("0.90") + (Decimal("0.22") * win_pct), Decimal("0.82"), Decimal("1.18"))
    defense = clamp(Decimal("0.92") + (Decimal("0.20") * win_pct), Decimal("0.82"), Decimal("1.20"))
    return offense, defense


def decompose_record_hfa(
    off_home: Decimal, def_home: Decimal, off_away: Decimal, def_away: Decimal
) -> Tuple[Decimal, Decimal]:
    off_def_home = clamp((off_home / max(Decimal("0.75"), def_away)) - Decimal("1"), Decimal("-0.25"), Decimal("0.25"))
    off_def_away = clamp((off_away / max(Decimal("0.75"), def_home)) - Decimal("1"), Decimal("-0.25"), Decimal("0.25"))
    margin = clamp((off_def_home - off_def_away) * Decimal(str(MARGIN_WEIGHT)), Decimal(str(-MAX_MARGIN)), Decimal(str(MAX_MARGIN))) + Decimal(str(HFA))
    total = Decimal(str(BASE_TOTAL)) + clamp(
        (off_def_home + off_def_away) * Decimal(str(TOTAL_WEIGHT)), Decimal(str(-MAX_TOTAL)), Decimal(str(MAX_TOTAL))
    )
    return margin, total


def record_spread_total(wins_home: int, losses_home: int, wins_away: int, losses_away: int) -> Tuple[float, float]:
    off_h, def_h = team_strength_from_record(wins_home, losses_home)
    off_a, def_a = team_strength_from_record(wins_away, losses_away)
    margin, total = decompose_record_hfa(off_h, def_h, off_a, def_a)
    return round4(-margin), round4(total)


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


def assert_reproduces_le2023_csv(close_path: str, baseline_path: str, close_sha: str, baseline_sha: str) -> Dict[str, Any]:
    """B-9: Decimal ROUND_HALF_UP vs pinned 502110cf. Tolerance 1e-4 (IMV-allowed).

    Cited case 2015 wk12 DAL-CAR total must be exactly 45.3563.
    """
    import csv
    import hashlib
    from pathlib import Path

    close = Path(close_path)
    baseline = Path(baseline_path)
    got_close = hashlib.sha256(close.read_bytes()).hexdigest()
    got_base = hashlib.sha256(baseline.read_bytes()).hexdigest()
    if got_close != close_sha:
        raise AssertionError(f"nflverse_close sha {got_close} != {close_sha}")
    if got_base != baseline_sha:
        raise AssertionError(f"record_baseline sha {got_base} != {baseline_sha}")
    schedule: List[Dict[str, Any]] = []
    with close.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            schedule.append(
                {
                    "season": int(row["season"]),
                    "week": int(row["week"]),
                    "home": row["home"],
                    "away": row["away"],
                    "home_score": row["home_score"],
                    "away_score": row["away_score"],
                }
            )
    book = build_record_book(schedule)
    n = 0
    n_outside = 0
    max_abs = 0.0
    dal_car = None
    with baseline.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            n += 1
            key = (int(row["season"]), int(row["week"]), alias(row["home"]), alias(row["away"]))
            rec = book.get(key)
            if rec is None:
                raise AssertionError(f"B-9 missing book row {key}")
            ds = abs(rec["record_spread"] - float(row["record_spread"]))
            dt = abs(rec["record_total"] - float(row["record_total"]))
            max_abs = max(max_abs, ds, dt)
            if ds > 1e-4 + 1e-12 or dt > 1e-4 + 1e-12:
                n_outside += 1
            if key == (2015, 12, "DAL", "CAR"):
                dal_car = rec["record_total"]
    if n_outside:
        raise AssertionError(f"B-9 method-vs-CSV {n_outside} rows outside 1e-4 (max_abs={max_abs})")
    if n != 2992:
        raise AssertionError(f"B-9 expected 2992 baseline rows, got {n}")
    if dal_car is None or abs(float(dal_car) - 45.3563) > 1e-12:
        raise AssertionError(f"B-9 2015 wk12 DAL-CAR total {dal_car} != 45.3563")
    w1m, w1t = week1_identity()
    if abs(w1m - 1.05) > 1e-12 or abs(w1t - 44.8435) > 1e-12:
        raise AssertionError(f"B-9 week-1 identity drifted {w1m} {w1t}")
    return {
        "n": n,
        "max_abs": max_abs,
        "n_outside_1e4": n_outside,
        "dal_car_2015_12_total": dal_car,
        "week1_margin": w1m,
        "week1_total": w1t,
        "rounding": "Decimal ROUND_HALF_UP",
        "tolerance": 1e-4,
    }
