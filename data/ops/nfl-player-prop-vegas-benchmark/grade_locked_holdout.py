"""Grade a LOCKED stake rule on a holdout/confirm pull batch.

Does NOT refit calibration intercepts or PLAY thresholds. Uses the same
frozen apply_prop_calibration + evaluate_prop_edge path as production.

Usage:
  /Users/ryankos/kosedge/.venv/bin/python3 grade_locked_holdout.py \\
      --pull-log pull_run_log_batch5_confirm.json \\
      --out enterprise_v2_confirm_offset3.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

MODEL_SERVICE_SRC = "/Users/ryankos/kosedge/services/model-service"
sys.path.insert(0, MODEL_SERVICE_SRC)

from src.services.nfl_player_prop_calibration import apply_prop_calibration  # noqa: E402
from src.services.nfl_prop_edge_policy import evaluate_prop_edge  # noqa: E402

OUTPUT_DIR = Path(__file__).parent
STAKE = 100.0
BLEND_MC = 0.60
BLEND_BASE = 0.40
DEFAULT_RULE_NAME = "calibrated_rec_z060_v1_2_provisional"


def american_profit(price: Optional[int], stake: float) -> float:
    if price is None:
        return 0.0
    if price < 0:
        return stake * (100.0 / abs(price))
    return stake * (price / 100.0)


def wilson_ci(wins: int, n: int, z: float = 1.96) -> Optional[Dict[str, Any]]:
    if n == 0:
        return None
    p = wins / n
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))) / denom
    return {"point": round(p, 4), "low": round(center - half, 4), "high": round(center + half, 4)}


def blend_mean_std(r: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    new_m, new_s = r.get("new_mean"), r.get("new_std")
    cur_m, cur_s = r.get("current_mean"), r.get("current_std")
    if new_m is None or new_s is None:
        if cur_m is None or cur_s is None:
            return None
        return float(cur_m), float(cur_s)
    if cur_m is None or cur_s is None:
        return float(new_m), float(new_s)
    mean = BLEND_MC * float(new_m) + BLEND_BASE * float(cur_m)
    var = (BLEND_MC * float(new_s)) ** 2 + (BLEND_BASE * float(cur_s)) ** 2
    return mean, math.sqrt(max(var, 0.65**2))


def summarize(rows: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    decided = [x for x in rows if x["outcome"] in ("win", "loss")]
    wins = sum(1 for x in decided if x["outcome"] == "win")
    staked = profit = 0.0
    n_bets = 0
    for x in decided:
        price = x.get("price")
        if price is None:
            continue
        n_bets += 1
        staked += STAKE
        if x["outcome"] == "win":
            profit += american_profit(int(price), STAKE)
        else:
            profit -= STAKE
    n = len(decided)
    return {
        "label": label,
        "n_decided": n,
        "wins": wins,
        "win_rate": round(wins / n, 4) if n else None,
        "wilson_95": wilson_ci(wins, n),
        "n_bets": n_bets,
        "staked": staked,
        "profit": round(profit, 2),
        "roi_pct": round(100.0 * profit / staked, 3) if staked > 0 else None,
        "clears_coin_flip_95": bool(wilson_ci(wins, n) and wilson_ci(wins, n)["low"] > 0.50) if n else False,
        "clears_minus110_breakeven_95": bool(wilson_ci(wins, n) and wilson_ci(wins, n)["low"] > 0.5238) if n else False,
    }


def load_holdout_keys(pull_log: Path) -> Set[Tuple[int, int, str, str]]:
    log = json.loads(pull_log.read_text())
    keys: Set[Tuple[int, int, str, str]] = set()
    for g in log.get("games_pulled") or []:
        keys.add((int(g["season"]), int(g["week"]), str(g["home_team"]), str(g["away_team"])))
    return keys


def record_in_holdout(r: Dict[str, Any], keys: Set[Tuple[int, int, str, str]]) -> bool:
    """Match via team/opponent against home/away (either orientation)."""
    season, week = int(r["season"]), int(r["week"])
    team, opp = str(r.get("team") or ""), str(r.get("opponent") or "")
    return (season, week, team, opp) in keys or (season, week, opp, team) in keys


def grade_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    graded: List[Dict[str, Any]] = []
    for r in records:
        blended = blend_mean_std(r)
        if blended is None:
            continue
        raw_mean, raw_std = blended
        market_key = str(r.get("market_key") or "")
        position = str(r.get("position") or "")
        line = float(r["line"])
        cal = apply_prop_calibration(
            model_mean=raw_mean,
            model_std=raw_std,
            market_key=market_key,
            market_line=None,
            role_confidence=0.8,
        )
        mean = float(cal["model_mean"])
        std = float(cal["model_std"])
        edge = evaluate_prop_edge(
            model_mean=mean,
            model_std=std,
            line=line,
            market_over_price=r.get("over_price"),
            market_under_price=r.get("under_price"),
            market_key=market_key,
            position=position,
            role_confidence=0.8,
            availability_confidence=0.8,
        )
        if edge.get("tag") != "PLAY" or not edge.get("stake_eligible"):
            continue
        side = str(edge.get("tag_side") or "").lower()
        if side not in ("over", "under"):
            continue
        actual = float(r["actual"])
        if actual == line:
            outcome = "push"
        elif (side == "over" and actual > line) or (side == "under" and actual < line):
            outcome = "win"
        else:
            outcome = "loss"
        price = r.get("over_price") if side == "over" else r.get("under_price")
        graded.append(
            {
                "season": r.get("season"),
                "week": r.get("week"),
                "team": r.get("team"),
                "opponent": r.get("opponent"),
                "player_name": r.get("player_name"),
                "position": position,
                "market_key": market_key,
                "line": line,
                "actual": actual,
                "mean": round(mean, 3),
                "side": side,
                "outcome": outcome,
                "price": price,
                "z_over": edge.get("z_over"),
                "tag_reason": edge.get("tag_reason"),
            }
        )
    return graded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pull-log",
        default="pull_run_log_batch5_confirm.json",
        help="Pull run log with games_pulled keys",
    )
    parser.add_argument("--out", default="enterprise_v2_confirm_offset3.json")
    parser.add_argument("--rule", default=DEFAULT_RULE_NAME)
    parser.add_argument("--residue-offset", type=int, default=3)
    parser.add_argument("--batch", type=int, default=5)
    args = parser.parse_args()

    pull_log = OUTPUT_DIR / args.pull_log
    holdout_keys = load_holdout_keys(pull_log)
    records = json.loads((OUTPUT_DIR / "raw_prop_records.json").read_text())
    holdout_records = [r for r in records if record_in_holdout(r, holdout_keys)]
    train_records = [r for r in records if not record_in_holdout(r, holdout_keys)]

    print(f"Holdout games in pull log: {len(holdout_keys)}")
    print(f"Records: holdout={len(holdout_records)} train/other={len(train_records)} total={len(records)}")

    holdout_plays = grade_records(holdout_records)
    train_plays = grade_records(train_records)

    by_market: Dict[str, Any] = {}
    for mk in ("pass_yds", "rush_yds", "rec_yds"):
        by_market[mk] = summarize([g for g in holdout_plays if g["market_key"] == mk], f"holdout {mk} PLAY")

    holdout_summary = summarize(holdout_plays, "holdout PLAY (locked rule)")
    train_summary = summarize(train_plays, "prior PLAY (same locked rule, excl. this holdout)")

    verdict: str
    n = holdout_summary.get("n_decided") or 0
    if n < 25:
        verdict = "INCONCLUSIVE — confirmation PLAY n too small"
    elif holdout_summary.get("roi_pct") is not None and holdout_summary["roi_pct"] > 0 and (holdout_summary.get("win_rate") or 0) >= 0.524:
        if holdout_summary.get("clears_minus110_breakeven_95"):
            verdict = "PROMOTE — confirmation clears −110 breakeven at 95% CI"
        elif holdout_summary.get("clears_coin_flip_95"):
            verdict = "SOFT PROMOTE — +EV point estimate and clears coin-flip CI; keep sizes modest"
        else:
            verdict = "DIRECTIONAL — point estimate +EV but CI includes 50%; keep provisional"
    elif holdout_summary.get("roi_pct") is not None and holdout_summary["roi_pct"] > -2 and (holdout_summary.get("win_rate") or 0) >= 0.51:
        verdict = "HOLD — roughly flat on confirmation; do not claim +EV"
    else:
        verdict = "FAIL — confirmation does not support the provisional rule; demote PLAY"

    report = {
        "rule": args.rule,
        "refit": False,
        "holdout_batch": args.batch,
        "holdout_residue_offset": args.residue_offset,
        "pull_log": str(pull_log.name),
        "n_holdout_games_pulled": len(holdout_keys),
        "n_holdout_records": len(holdout_records),
        "holdout_play": holdout_summary,
        "prior_play_same_rule": train_summary,
        "holdout_by_market": by_market,
        "verdict": verdict,
        "breakeven_win_rate_at_minus110": 0.5238,
    }
    out = OUTPUT_DIR / args.out
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
