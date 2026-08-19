#!/usr/bin/env python3
"""Pass-yds-only residual study. Research only — does not ungate weekly props.

Frozen prop-enterprise-cal-v1 stays live. Rush already failed the actual-MAE
gate, so a pass-only intercept swap is not a product change.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
sys.path.insert(0, ROOT)
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from scripts.nfl.prop_archive_calibration_holdout import (  # noqa: E402
    HOLDOUT_SEASON,
    TRAIN_SEASONS,
    _lag_pred,
    _load_db,
    _mae,
)
from src.services.nfl_player_prop_calibration import (  # noqa: E402
    FROZEN_MEAN_INTERCEPT,
    apply_prop_calibration,
    fit_prop_calibration_from_points,
    frozen_calibration_for,
)
from src.services.nfl_warehouse.odds_lake import team_abbr  # noqa: E402
from src.services.nfl_warehouse.prop_join import (  # noqa: E402
    iter_prop_closes,
    pick_close_by_player,
)

OUT = os.path.join(ROOT, "data", "ops", "nfl-pass-yds-residual-holdout.json")
MARKET = "pass_yds"
CLOSE_BUCKETS = ((0, 225), (225, 275), (275, 325), (325, 10_000))


def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return round(sum(xs) / len(xs), 4)


def _bucket_label(close: float) -> str:
    for lo, hi in CLOSE_BUCKETS:
        if lo <= close < hi:
            return f"{lo}-{hi - 1}" if hi < 10_000 else f"{lo}+"
    return "other"


def _slice(rows: List[Dict[str, Any]], pred_key: str, target_key: str) -> Dict[str, Any]:
    pairs = [(float(r[pred_key]), float(r[target_key])) for r in rows]
    residuals = [a - b for a, b in pairs]
    return {
        "n": len(rows),
        "mae": _mae(pairs),
        "mean_residual": _mean(residuals),
        "under_rate": (
            round(sum(1 for x in residuals if x < 0) / len(residuals), 4) if residuals else None
        ),
    }


def main() -> int:
    print("loading postgres usage/baselines/schedule...", flush=True)
    sched, usage, baseline, by_player = _load_db()
    print("streaming owned pass_yds closes...", flush=True)
    closes = pick_close_by_player(iter_prop_closes(markets=("player_pass_yds",)))
    print(f"unique pass_yds closes={len(closes)}", flush=True)

    joined: List[Dict[str, Any]] = []
    for row in closes:
        home = team_abbr(str(row.get("home") or ""))
        away = team_abbr(str(row.get("away") or ""))
        hit = sched.get((str(row.get("game_date") or ""), home, away))
        if not hit:
            continue
        season, week = hit
        usage_row = usage.get((season, week, home, row["player_key"])) or usage.get(
            (season, week, away, row["player_key"])
        )
        if not usage_row or usage_row.get("pass_yards") is None:
            continue
        actual = float(usage_row["pass_yards"])
        team = str(usage_row["team"])
        base = baseline.get((season, week, team, row["player_key"]))
        pred = None
        src = None
        if base and base.get("pass_yards_mean") is not None:
            pred = float(base["pass_yards_mean"])
            src = "baseline_2025"
        else:
            pred = _lag_pred(usage_row, by_player, MARKET)
            src = "lag3_usage" if pred is not None else None
        if pred is None:
            continue
        close = float(row["line"])
        frozen = apply_prop_calibration(
            model_mean=pred,
            model_std=1.0,
            market_key=MARKET,
            calibration=frozen_calibration_for(MARKET),
            market_line=close,
        )
        joined.append(
            {
                "season": season,
                "week": week,
                "pred": pred,
                "actual": actual,
                "close": close,
                "frozen_mean": float(frozen["model_mean"]),
                "pred_source": src,
                "close_bucket": _bucket_label(close),
            }
        )

    train = [r for r in joined if r["season"] in TRAIN_SEASONS]
    hold = [r for r in joined if r["season"] == HOLDOUT_SEASON]
    cand = fit_prop_calibration_from_points(
        [{"pred": r["pred"], "actual": r["actual"]} for r in train],
        market_key=MARKET,
    )
    for r in hold:
        applied = apply_prop_calibration(
            model_mean=r["pred"],
            model_std=1.0,
            market_key=MARKET,
            calibration=cand,
            market_line=r["close"],
        )
        r["candidate_mean"] = float(applied["model_mean"])

    by_bucket: Dict[str, Any] = {}
    for label in [f"{lo}-{hi - 1}" if hi < 10_000 else f"{lo}+" for lo, hi in CLOSE_BUCKETS]:
        rows = [r for r in hold if r["close_bucket"] == label]
        by_bucket[label] = {
            "raw_vs_close": _slice(rows, "pred", "close"),
            "frozen_vs_close": _slice(rows, "frozen_mean", "close"),
            "candidate_vs_close": _slice(rows, "candidate_mean", "close"),
            "raw_vs_actual": _slice(rows, "pred", "actual"),
            "frozen_vs_actual": _slice(rows, "frozen_mean", "actual"),
            "candidate_vs_actual": _slice(rows, "candidate_mean", "actual"),
        }

    frozen_close = _slice(hold, "frozen_mean", "close")
    cand_close = _slice(hold, "candidate_mean", "close")
    frozen_act = _slice(hold, "frozen_mean", "actual")
    cand_act = _slice(hold, "candidate_mean", "actual")
    cand_beats = bool(
        hold
        and cand_close["mae"] is not None
        and frozen_close["mae"] is not None
        and cand_act["mae"] is not None
        and frozen_act["mae"] is not None
        and cand_close["mae"] < frozen_close["mae"]
        and cand_act["mae"] <= frozen_act["mae"]
    )

    report = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "product": False,
        "market": MARKET,
        "coverage": {
            "unique_closes": len(closes),
            "joined": len(joined),
            "train_n": len(train),
            "holdout_n": len(hold),
        },
        "frozen_intercept": FROZEN_MEAN_INTERCEPT.get(MARKET),
        "candidate_intercept": cand.intercept,
        "candidate_source": cand.source,
        "holdout": {
            "raw_vs_close": _slice(hold, "pred", "close"),
            "frozen_vs_close": frozen_close,
            "candidate_vs_close": cand_close,
            "raw_vs_actual": _slice(hold, "pred", "actual"),
            "frozen_vs_actual": frozen_act,
            "candidate_vs_actual": cand_act,
        },
        "holdout_by_close_bucket": by_bucket,
        "gates": {
            "ungate_weekly_props": False,
            "replace_frozen_intercepts": False,
            "replace_pass_yds_intercept_only": False,
            "candidate_beats_frozen_pass_only": cand_beats,
            "NFL_WEEKLY_PROPS_LIVE": False,
        },
        "note": (
            "Pass-only residual study. Frozen cal-v1 stays live. Do not ungate "
            "weekly props or swap intercepts: rush already failed vs actual, and "
            "the live calibration is one shared frozen dict."
        ),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
