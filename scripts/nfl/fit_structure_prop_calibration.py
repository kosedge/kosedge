#!/usr/bin/env python3
"""Fit structure-trained prop cal on post-Phase-2 shared baseline means.

Train: 2023–2024 structure baselines vs actuals (weeks 4–17).
Holdout: 2025. Compare structure-only / frozen / structure-cal.

Does not flip NFL_WEEKLY_PROPS_LIVE. Writes:
  data/ops/nfl-spine-phase3-structure-cal.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))
sys.path.insert(0, ROOT)
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from scripts.nfl.prop_archive_calibration_holdout import (  # noqa: E402
    ACTUAL_FIELD,
    _mae,
)
from src.services.nfl_player_prop_calibration import (  # noqa: E402
    FROZEN_MEAN_INTERCEPT,
    FROZEN_STD_MULTIPLIER,
    apply_prop_calibration,
    fit_prop_calibration_from_points,
    frozen_calibration_for,
)
from src.services.nfl_warehouse.odds_lake import team_abbr  # noqa: E402
from src.services.nfl_warehouse.prop_join import (  # noqa: E402
    iter_prop_closes,
    normalize_player_key,
    pick_close_by_player,
)

CORE = ("pass_yds", "rush_yds", "rec_yds", "receptions")
PRED_FIELD = {
    "pass_yds": "pass_yards_mean",
    "rush_yds": "rush_yards_mean",
    "rec_yds": "receiving_yards_mean",
    "receptions": "receptions_mean",
}
OUT = os.path.join(ROOT, "data", "ops", "nfl-spine-phase3-structure-cal.json")


def _mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def _slice(rows: List[Dict[str, Any]], pred: str, target: str) -> Dict[str, Any]:
    pairs = [(float(r[pred]), float(r[target])) for r in rows]
    res = [a - b for a, b in pairs]
    return {
        "n": len(rows),
        "mae": _mae(pairs),
        "mean_residual": _mean(res),
    }


def main() -> int:
    engine = create_engine(os.environ["DATABASE_URL"])
    sched: Dict[Tuple[str, str, str], Tuple[int, int]] = {}
    usage: Dict[Any, Dict[str, Any]] = {}
    baseline: Dict[Any, Dict[str, Any]] = {}
    with engine.connect() as conn:
        for r in conn.execute(
            text(
                """
                SELECT season, week, game_date, home_team, away_team
                FROM nfl_dp_schedules
                WHERE season BETWEEN 2023 AND 2025 AND home_score IS NOT NULL
                """
            )
        ):
            day = str(r.game_date or "")[:10]
            home = team_abbr(str(r.home_team))
            away = team_abbr(str(r.away_team))
            if day and home and away:
                sched[(day, home, away)] = (int(r.season), int(r.week))
        for r in conn.execute(
            text(
                """
                SELECT season, week, team, player_id, player_name, position,
                       pass_yards, rush_yards, receiving_yards, receptions
                FROM nfl_dp_player_usage_weekly
                WHERE season BETWEEN 2023 AND 2025
                """
            )
        ):
            key = (int(r.season), int(r.week), str(r.team), normalize_player_key(str(r.player_name or "")))
            usage[key] = dict(r._mapping)
        for r in conn.execute(
            text(
                """
                SELECT season, week, team, player_name,
                       pass_yards_mean, rush_yards_mean, receiving_yards_mean, receptions_mean
                FROM nfl_player_projection_baselines
                WHERE model_version = 'nfl-player-v1'
                  AND season BETWEEN 2023 AND 2025
                  AND week BETWEEN 4 AND 17
                """
            )
        ):
            key = (int(r.season), int(r.week), str(r.team), normalize_player_key(str(r.player_name or "")))
            baseline[key] = dict(r._mapping)

    print(f"sched={len(sched)} usage={len(usage)} baselines={len(baseline)}", flush=True)
    closes = pick_close_by_player(iter_prop_closes())
    joined: List[Dict[str, Any]] = []
    for row in closes:
        home = team_abbr(str(row.get("home") or ""))
        away = team_abbr(str(row.get("away") or ""))
        hit = sched.get((str(row.get("game_date") or ""), home, away))
        if not hit:
            continue
        season, week = hit
        if week < 4 or week > 17:
            continue
        usage_row = usage.get((season, week, home, row["player_key"])) or usage.get(
            (season, week, away, row["player_key"])
        )
        if not usage_row:
            continue
        mk = str(row["market"])
        if mk not in CORE:
            continue
        field = ACTUAL_FIELD[mk]
        if usage_row.get(field) is None:
            continue
        team = str(usage_row["team"])
        base = baseline.get((season, week, team, row["player_key"]))
        if not base or base.get(PRED_FIELD[mk]) is None:
            continue
        pred = float(base[PRED_FIELD[mk]])
        close = float(row["line"])
        actual = float(usage_row[field])
        frozen = apply_prop_calibration(
            model_mean=pred,
            model_std=1.0,
            market_key=mk,
            calibration=frozen_calibration_for(mk),
            market_line=close,
        )
        joined.append(
            {
                "season": season,
                "week": week,
                "market": mk,
                "pred": pred,
                "actual": actual,
                "close": close,
                "frozen_mean": float(frozen["model_mean"]),
            }
        )

    train = [r for r in joined if r["season"] in (2023, 2024)]
    hold = [r for r in joined if r["season"] == 2025]
    print(f"joined={len(joined)} train={len(train)} hold={len(hold)}", flush=True)

    candidate = {}
    for mk in CORE:
        pts = [{"pred": r["pred"], "actual": r["actual"]} for r in train if r["market"] == mk]
        candidate[mk] = fit_prop_calibration_from_points(pts, market_key=mk, min_sample_size=80)
        print(
            f"  fit {mk}: n={candidate[mk].sample_size} intercept={candidate[mk].intercept:.4f} "
            f"std_mult={candidate[mk].std_multiplier:.4f} source={candidate[mk].source}"
        )

    for r in hold:
        applied = apply_prop_calibration(
            model_mean=r["pred"],
            model_std=1.0,
            market_key=r["market"],
            calibration=candidate[r["market"]],
            market_line=r["close"],
        )
        r["structure_cal_mean"] = float(applied["model_mean"])

    by_mk: Dict[str, Any] = {}
    promote_ok = True
    reasons: List[str] = []
    for mk in CORE:
        rows = [r for r in hold if r["market"] == mk]
        raw_act = _slice(rows, "pred", "actual")
        frz_act = _slice(rows, "frozen_mean", "actual")
        cand_act = _slice(rows, "structure_cal_mean", "actual")
        raw_close = _slice(rows, "pred", "close")
        frz_close = _slice(rows, "frozen_mean", "close")
        cand_close = _slice(rows, "structure_cal_mean", "close")
        by_mk[mk] = {
            "structure_only_vs_actual": raw_act,
            "frozen_vs_actual": frz_act,
            "structure_cal_vs_actual": cand_act,
            "structure_only_vs_close": raw_close,
            "frozen_vs_close": frz_close,
            "structure_cal_vs_close": cand_close,
            "frozen_intercept": FROZEN_MEAN_INTERCEPT.get(mk),
            "structure_intercept": candidate[mk].intercept,
            "structure_std_multiplier": candidate[mk].std_multiplier,
            "structure_sample_size": candidate[mk].sample_size,
            "structure_source": candidate[mk].source,
        }
        # Reject if cand worsens actual vs structure-only materially, or vs frozen on pass
        if cand_act["mae"] > raw_act["mae"] + 0.25:
            promote_ok = False
            reasons.append(f"{mk}: structure_cal actual MAE worse than structure-only")
        if mk == "rush_yds" and cand_act["mae"] > raw_act["mae"] + 0.05:
            promote_ok = False
            reasons.append("rush: structure_cal regresses vs structure-only actual")
        if cand_act["mae"] > frz_act["mae"] + 0.25 and cand_close["mae"] > frz_close["mae"] + 0.5:
            promote_ok = False
            reasons.append(f"{mk}: structure_cal loses both actual and close vs frozen")

    # Prefer structure cal only if it beats frozen on actual for all markets
    # without rush regress vs structure-only, and close not materially worse.
    beats_frozen = all(
        by_mk[mk]["structure_cal_vs_actual"]["mae"] <= by_mk[mk]["frozen_vs_actual"]["mae"] + 0.15
        for mk in CORE
    )
    close_ok = all(
        by_mk[mk]["structure_cal_vs_close"]["mae"] <= by_mk[mk]["frozen_vs_close"]["mae"] + 0.75
        for mk in CORE
    )
    rush_ok = by_mk["rush_yds"]["structure_cal_vs_actual"]["mae"] <= by_mk["rush_yds"]["structure_only_vs_actual"]["mae"] + 0.05
    activate = bool(promote_ok and beats_frozen and close_ok and rush_ok and all(candidate[m].source != "identity" for m in CORE))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "train_seasons": [2023, 2024],
        "holdout_season": 2025,
        "weeks": "4-17",
        "pred_source": "nfl_player_projection_baselines structure rematerialize",
        "markets": by_mk,
        "decision": {
            "activate_structure_cal": activate,
            "ACTIVE_PROP_CAL_SOURCE": "structure" if activate else "frozen",
            "beats_frozen_actual": beats_frozen,
            "close_ok": close_ok,
            "rush_ok": rush_ok,
            "reasons": reasons,
            "NFL_WEEKLY_PROPS_LIVE": False,
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(json.dumps(payload["decision"], indent=2))
    print(f"wrote {OUT}")

    if activate:
        # Print constants for ops to paste — do not auto-edit live module unless activate.
        print("STRUCTURE_MEAN_INTERCEPT = {")
        for mk in CORE:
            print(f'    "{mk}": {candidate[mk].intercept:.4f},')
        print("}")
    return 0 if True else 1


if __name__ == "__main__":
    raise SystemExit(main())
