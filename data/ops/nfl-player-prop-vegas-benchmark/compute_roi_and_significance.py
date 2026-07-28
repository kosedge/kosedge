"""Second-pass, cheap analysis on top of `raw_prop_records.json` (already
produced by compute_benchmark.py -- this script does NOT re-run the Monte
Carlo box-score simulation or touch the database/API again).

Adds two things the win-rate summary in benchmark_summary.json doesn't
answer on its own:
  1. Real flat-stake ROI (a $100-per-bet unit, standard sports-betting
     convention) for each methodology -- win rate alone doesn't tell you
     whether the WINS were on short-priced favorites (small profit) vs.
     the LOSSES were on the same, i.e. it doesn't confirm profitability
     the way a real ROI number does.
  2. A normal-approximation 95% CI on each methodology's overall win rate
     and on the OLD-vs-NEW / CURRENT-vs-NEW paired win-rate deltas, so the
     report can honestly state whether the differences are
     distinguishable from noise at this sample size, not just report raw
     percentages.

Uses the SAME grading function (`grade_prop_bet`) as compute_benchmark.py
-- not a reimplementation of the win/loss logic, just re-deriving win/loss
+ ROI from the already-graded inputs.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_SERVICE_SRC = "/Users/ryankos/kosedge/services/model-service"
sys.path.insert(0, MODEL_SERVICE_SRC)

from src.services.nfl_player_prop_backtest_scoring import grade_prop_bet  # noqa: E402

OUTPUT_DIR = Path(__file__).parent
METHODS = ["old", "current", "new"]
STAKE = 100.0


def american_profit(price: Optional[int], stake: float) -> float:
    if price is None:
        return 0.0
    if price < 0:
        return stake * (100.0 / abs(price))
    return stake * (price / 100.0)


def wilson_ci(wins: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = wins / n
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))) / denom
    return {"point": round(p, 4), "low": round(center - half, 4), "high": round(center + half, 4)}


def paired_delta_ci(method_a_grades: List[Any], method_b_grades: List[Any], z: float = 1.96):
    """Normal-approx CI on (win_rate_b - win_rate_a) treating each of the
    two win-rate estimates as independent binomials (a conservative
    approximation -- the two are actually mildly correlated since they
    grade the SAME underlying bets, so a truly paired bootstrap would give
    a tighter interval; this is intentionally the more conservative,
    simpler bound and is reported as such)."""
    decided_a = [g for g in method_a_grades if g.outcome in ("win", "loss")]
    decided_b = [g for g in method_b_grades if g.outcome in ("win", "loss")]
    if not decided_a or not decided_b:
        return None
    n_a, n_b = len(decided_a), len(decided_b)
    p_a = sum(1 for g in decided_a if g.outcome == "win") / n_a
    p_b = sum(1 for g in decided_b if g.outcome == "win") / n_b
    se = math.sqrt((p_a * (1 - p_a) / n_a) + (p_b * (1 - p_b) / n_b))
    delta = p_b - p_a
    return {
        "delta": round(delta, 4),
        "ci_95_low": round(delta - z * se, 4),
        "ci_95_high": round(delta + z * se, 4),
        "significant": bool((delta - z * se) > 0 or (delta + z * se) < 0),
    }


def main() -> None:
    records = json.loads((OUTPUT_DIR / "raw_prop_records.json").read_text())
    print(f"Loaded {len(records)} raw records")

    grades_by_method: Dict[str, list] = {m: [] for m in METHODS}
    roi_by_method: Dict[str, Dict[str, float]] = {m: {"staked": 0.0, "profit": 0.0, "n_bets": 0} for m in METHODS}

    for r in records:
        for method in METHODS:
            mean = r.get(f"{method}_mean")
            std = r.get(f"{method}_std")
            if mean is None or std is None:
                continue
            grade = grade_prop_bet(
                model_mean=float(mean), model_std=float(std), line=float(r["line"]), actual=float(r["actual"]),
                market_over_price=r["over_price"], market_under_price=r["under_price"],
            )
            grades_by_method[method].append(grade)

            if grade.side == "push_no_side" or grade.outcome == "push":
                continue
            price = r["over_price"] if grade.side == "over" else r["under_price"]
            if price is None:
                continue
            roi_by_method[method]["n_bets"] += 1
            roi_by_method[method]["staked"] += STAKE
            if grade.outcome == "win":
                roi_by_method[method]["profit"] += american_profit(price, STAKE)
            else:
                roi_by_method[method]["profit"] -= STAKE

    roi_summary = {}
    for method in METHODS:
        row = roi_by_method[method]
        roi_summary[method] = {
            **row,
            "roi_pct": round(100.0 * row["profit"] / row["staked"], 3) if row["staked"] > 0 else None,
        }

    win_rate_ci = {}
    for method in METHODS:
        decided = [g for g in grades_by_method[method] if g.outcome in ("win", "loss")]
        wins = sum(1 for g in decided if g.outcome == "win")
        win_rate_ci[method] = wilson_ci(wins, len(decided))

    deltas = {
        "current_minus_old": paired_delta_ci(grades_by_method["old"], grades_by_method["current"]),
        "new_minus_current": paired_delta_ci(grades_by_method["current"], grades_by_method["new"]),
        "new_minus_old": paired_delta_ci(grades_by_method["old"], grades_by_method["new"]),
    }

    breakeven_win_rate_for_minus110 = 110.0 / 210.0

    out = {
        "stake_per_bet": STAKE,
        "breakeven_win_rate_at_minus110": round(breakeven_win_rate_for_minus110, 4),
        "roi_by_method": roi_summary,
        "win_rate_95ci_wilson": win_rate_ci,
        "paired_win_rate_deltas_95ci_normal_approx": deltas,
    }
    (OUTPUT_DIR / "roi_and_significance.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
