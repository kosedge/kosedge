"""Grade enterprise prop policy v2 against DB closing lines in raw_prop_records.json.

Applies the same 60/40 blend + frozen mean/std calibration + PLAY/WATCH policy
used in production materialize. No Odds API calls.

Usage: /Users/ryankos/kosedge/.venv/bin/python3 grade_enterprise_tags.py
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
from src.services.nfl_player_prop_calibration import apply_prop_calibration  # noqa: E402
from src.services.nfl_prop_edge_policy import evaluate_prop_edge  # noqa: E402

OUTPUT_DIR = Path(__file__).parent
STAKE = 100.0
BLEND_MC = 0.60
BLEND_BASE = 0.40


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


def blend_mean_std(r: Dict[str, Any]) -> Optional[tuple[float, float]]:
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
    std = math.sqrt(max(var, 0.65**2))
    return mean, std


def summarize_slice(rows: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    decided = [x for x in rows if x["outcome"] in ("win", "loss")]
    wins = sum(1 for x in decided if x["outcome"] == "win")
    staked = 0.0
    profit = 0.0
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
        "n_rows": len(rows),
        "n_decided": n,
        "wins": wins,
        "win_rate": round(wins / n, 4) if n else None,
        "wilson_95": wilson_ci(wins, n),
        "n_bets": n_bets,
        "staked": staked,
        "profit": round(profit, 2),
        "roi_pct": round(100.0 * profit / staked, 3) if staked > 0 else None,
        "breakeven_note": "≈52.4% needed at typical −110",
    }


def main() -> None:
    records_path = OUTPUT_DIR / "raw_prop_records.json"
    records = json.loads(records_path.read_text())
    print(f"Loaded {len(records)} records from {records_path.name}")

    graded: List[Dict[str, Any]] = []
    tag_counts: Dict[str, int] = {"PLAY": 0, "WATCH": 0, "PASS": 0}
    reason_counts: Dict[str, int] = {}

    for r in records:
        blended = blend_mean_std(r)
        if blended is None:
            continue
        raw_mean, raw_std = blended
        market_key = str(r.get("market_key") or "")
        position = str(r.get("position") or "")
        line = float(r["line"])
        # No market shrink on solid-role path (matches production stake tagging).
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
            role_confidence=0.7,
            availability_confidence=0.8,
        )
        grade = grade_prop_bet(
            model_mean=mean,
            model_std=std,
            line=line,
            actual=float(r["actual"]),
            market_over_price=r.get("over_price"),
            market_under_price=r.get("under_price"),
        )
        tag = str(edge.get("tag") or "PASS")
        if tag == "LEAN":
            tag = "WATCH"
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        reason = str(edge.get("tag_reason") or "")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        tag_side = edge.get("tag_side")
        if tag in ("PLAY", "WATCH") and tag_side in ("Over", "Under"):
            side = tag_side.lower()
            actual = float(r["actual"])
            if actual == line:
                outcome = "push"
            elif (side == "over" and actual > line) or (side == "under" and actual < line):
                outcome = "win"
            else:
                outcome = "loss"
        else:
            side = grade.side
            outcome = grade.outcome

        price = None
        if side == "over":
            price = r.get("over_price")
        elif side == "under":
            price = r.get("under_price")

        graded.append(
            {
                "season": r.get("season"),
                "week": r.get("week"),
                "player_name": r.get("player_name"),
                "position": position,
                "market_key": market_key,
                "line": r.get("line"),
                "actual": r.get("actual"),
                "mean": round(mean, 3),
                "std": round(std, 3),
                "tag": tag,
                "tag_side": edge.get("tag_side"),
                "tag_reason": reason,
                "stake_eligible": bool(edge.get("stake_eligible")),
                "size_down": edge.get("size_down"),
                "z_over": edge.get("z_over"),
                "side": side,
                "outcome": outcome,
                "price": price,
                "conviction": grade.conviction,
            }
        )

    seasons = sorted({g["season"] for g in graded if g.get("season") is not None})
    n_game_keys = len(
        {
            (r.get("season"), r.get("week"), r.get("team"), r.get("opponent"))
            for r in records
            if r.get("season") is not None
        }
    )

    slices = {
        "blanket_calibrated": summarize_slice(graded, "all calibrated model-favored sides"),
        "play_only": summarize_slice([g for g in graded if g["tag"] == "PLAY"], "PLAY stake tags only"),
        "watch_only": summarize_slice([g for g in graded if g["tag"] == "WATCH"], "WATCH informational"),
        "play_or_watch": summarize_slice(
            [g for g in graded if g["tag"] in ("PLAY", "WATCH")], "PLAY+WATCH"
        ),
        "high_conviction_blanket": summarize_slice(
            [g for g in graded if g.get("conviction") == "high"],
            "legacy high-conviction (|z|>=0.5) blanket",
        ),
    }

    by_market: Dict[str, Any] = {}
    for mk in ("pass_yds", "rush_yds", "rec_yds"):
        by_market[mk] = {
            "blanket": summarize_slice([g for g in graded if g["market_key"] == mk], f"{mk} blanket"),
            "play_only": summarize_slice(
                [g for g in graded if g["market_key"] == mk and g["tag"] == "PLAY"],
                f"{mk} PLAY",
            ),
        }

    report = {
        "policy_version": "enterprise-v2-play-watch",
        "source_records": str(records_path),
        "n_records": len(records),
        "n_graded": len(graded),
        "n_team_game_sides_approx": n_game_keys,
        "seasons": seasons,
        "blend": {"mc_weight": BLEND_MC, "baseline_weight": BLEND_BASE},
        "calibration": "frozen prop-enterprise-cal-v1 + mild market shrink",
        "tag_counts": tag_counts,
        "tag_reason_counts": dict(sorted(reason_counts.items(), key=lambda kv: -kv[1])),
        "slices": slices,
        "by_market": by_market,
        "honest_read": (
            "PLAY must clear ~52.4% at −110 to be +EV. "
            "Enterprise v2 is intentionally sparse (pass_yds primary). "
            "If PLAY Wilson CI still includes 50%, treat as unproven — "
            "do not size up without a fresh residue-class holdout."
        ),
    }

    out = OUTPUT_DIR / "enterprise_tag_benchmark.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
