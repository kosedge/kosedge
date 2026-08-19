#!/usr/bin/env python3
"""Join owned prop closes to usage actuals + kickoff-safe preds; holdout only.

Does NOT flip NFL_WEEKLY_PROPS_LIVE. Frozen prop-enterprise-cal-v1 stays live
until holdout residual vs close AND vs actual both improve.
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
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_player_prop_calibration import (  # noqa: E402
    FROZEN_MEAN_INTERCEPT,
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

OUT = os.path.join(ROOT, "data", "ops", "nfl-prop-archive-calibration-holdout.json")
HOLDOUT_SEASON = 2025
TRAIN_SEASONS = {2023, 2024}
CORE = ("pass_yds", "rush_yds", "rec_yds", "receptions")
ACTUAL_FIELD = {
    "pass_yds": "pass_yards",
    "rush_yds": "rush_yards",
    "rec_yds": "receiving_yards",
    "receptions": "receptions",
    "anytime_td": "touchdowns_scored",
}
PRED_FIELD = {
    "pass_yds": "pass_yards_mean",
    "rush_yds": "rush_yards_mean",
    "rec_yds": "receiving_yards_mean",
    "receptions": "receptions_mean",
}


def _mae(pairs: List[Tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    return round(sum(abs(a - b) for a, b in pairs) / len(pairs), 4)


def _load_db() -> Tuple[Dict[Tuple[str, str, str], Tuple[int, int]], Dict[Any, Dict[str, Any]], Dict[Any, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    engine = create_engine(os.environ["DATABASE_URL"])
    sched: Dict[Tuple[str, str, str], Tuple[int, int]] = {}
    usage: Dict[Any, Dict[str, Any]] = {}
    baseline: Dict[Any, Dict[str, Any]] = {}
    by_player: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
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
                       pass_yards, rush_yards, receiving_yards, receptions, touchdowns_scored
                FROM nfl_dp_player_usage_weekly
                WHERE season BETWEEN 2023 AND 2025
                """
            )
        ):
            key = (int(r.season), int(r.week), str(r.team), normalize_player_key(str(r.player_name or "")))
            rec = dict(r._mapping)
            rec["player_key"] = key[3]
            usage[key] = rec
            if r.player_id:
                by_player[str(r.player_id)].append(rec)
        for r in conn.execute(
            text(
                """
                SELECT season, week, team, player_name,
                       pass_yards_mean, rush_yards_mean, receiving_yards_mean, receptions_mean
                FROM nfl_player_projection_baselines
                WHERE model_version = 'nfl-player-v1' AND season BETWEEN 2024 AND 2025
                """
            )
        ):
            key = (int(r.season), int(r.week), str(r.team), normalize_player_key(str(r.player_name or "")))
            baseline[key] = dict(r._mapping)
    for pid in by_player:
        by_player[pid].sort(key=lambda x: (int(x["season"]), int(x["week"])))
    return sched, usage, baseline, by_player


def _lag_pred(usage_row: Dict[str, Any], by_player: Dict[str, List[Dict[str, Any]]], market: str) -> Optional[float]:
    pid = str(usage_row.get("player_id") or "")
    field = ACTUAL_FIELD.get(market)
    if not pid or not field:
        return None
    prior = [
        float(r[field])
        for r in by_player.get(pid, [])
        if (int(r["season"]), int(r["week"])) < (int(usage_row["season"]), int(usage_row["week"]))
        and r.get(field) is not None
    ]
    if len(prior) < 2:
        return None
    return sum(prior[-3:]) / min(3, len(prior[-3:]))


def main() -> int:
    print("loading postgres usage/baselines/schedule...", flush=True)
    sched, usage, baseline, by_player = _load_db()
    print(f"sched={len(sched)} usage={len(usage)} baselines={len(baseline)}", flush=True)
    print("streaming owned prop closes...", flush=True)
    closes = pick_close_by_player(iter_prop_closes())
    print(f"unique player-market closes={len(closes)}", flush=True)

    joined: List[Dict[str, Any]] = []
    n_name = 0
    n_pred = 0
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
        if not usage_row:
            continue
        n_name += 1
        mk = str(row["market"])
        actual_field = ACTUAL_FIELD.get(mk)
        if not actual_field or usage_row.get(actual_field) is None:
            continue
        actual = float(usage_row[actual_field])
        team = str(usage_row["team"])
        base = baseline.get((season, week, team, row["player_key"]))
        pred = None
        src = None
        if base and PRED_FIELD.get(mk) and base.get(PRED_FIELD[mk]) is not None:
            pred = float(base[PRED_FIELD[mk]])
            src = "baseline_2025"
        else:
            pred = _lag_pred(usage_row, by_player, mk)
            src = "lag3_usage" if pred is not None else None
        if pred is None:
            continue
        n_pred += 1
        frozen = apply_prop_calibration(
            model_mean=pred,
            model_std=1.0,
            market_key=mk,
            calibration=frozen_calibration_for(mk),
            market_line=float(row["line"]),
        )
        joined.append(
            {
                "season": season,
                "week": week,
                "market": mk,
                "pred": pred,
                "actual": actual,
                "close": float(row["line"]),
                "frozen_mean": float(frozen["model_mean"]),
                "pred_source": src,
            }
        )

    train = [r for r in joined if r["season"] in TRAIN_SEASONS and r["market"] in CORE]
    hold = [r for r in joined if r["season"] == HOLDOUT_SEASON and r["market"] in CORE]
    candidate = {}
    for mk in CORE:
        pts = [{"pred": r["pred"], "actual": r["actual"]} for r in train if r["market"] == mk]
        candidate[mk] = fit_prop_calibration_from_points(pts, market_key=mk)

    by_mkt: Dict[str, Any] = {}
    ungate = False
    improve_close = True
    improve_actual = True
    for mk in CORE:
        h = [r for r in hold if r["market"] == mk]
        raw_vs_close = _mae([(r["pred"], r["close"]) for r in h])
        frozen_vs_close = _mae([(r["frozen_mean"], r["close"]) for r in h])
        raw_vs_act = _mae([(r["pred"], r["actual"]) for r in h])
        frozen_vs_act = _mae([(r["frozen_mean"], r["actual"]) for r in h])
        cand = candidate[mk]
        cand_means = []
        for r in h:
            applied = apply_prop_calibration(
                model_mean=r["pred"],
                model_std=1.0,
                market_key=mk,
                calibration=cand,
                market_line=r["close"],
            )
            cand_means.append((float(applied["model_mean"]), r["close"], r["actual"]))
        cand_vs_close = _mae([(m, c) for m, c, _ in cand_means])
        cand_vs_act = _mae([(m, a) for m, _, a in cand_means])
        by_mkt[mk] = {
            "holdout_n": len(h),
            "raw_mae_vs_close": raw_vs_close,
            "frozen_mae_vs_close": frozen_vs_close,
            "candidate_mae_vs_close": cand_vs_close,
            "raw_mae_vs_actual": raw_vs_act,
            "frozen_mae_vs_actual": frozen_vs_act,
            "candidate_mae_vs_actual": cand_vs_act,
            "candidate_intercept": cand.intercept,
            "frozen_intercept": FROZEN_MEAN_INTERCEPT.get(mk),
            "candidate_source": cand.source,
        }
        if len(h) < 80:
            improve_close = False
            improve_actual = False
            continue
        if frozen_vs_close is None or raw_vs_close is None or frozen_vs_close >= raw_vs_close:
            improve_close = False
        if frozen_vs_act is None or raw_vs_act is None or frozen_vs_act > raw_vs_act:
            improve_actual = False

    # Ungate only if frozen (or a better candidate) beats raw vs close AND does not
    # worsen actual MAE. This will stay false unless both clear.
    ungate = False

    report = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "product": False,
        "coverage": {
            "unique_closes": len(closes),
            "name_joined": n_name,
            "pred_joined": n_pred,
            "train_n": len(train),
            "holdout_n": len(hold),
        },
        "frozen": FROZEN_MEAN_INTERCEPT,
        "by_market": by_mkt,
        "gates": {
            "ungate_weekly_props": ungate,
            "replace_frozen_intercepts": False,
            "frozen_beats_raw_vs_close": improve_close,
            "frozen_does_not_worsen_actual": improve_actual,
            "NFL_WEEKLY_PROPS_LIVE": False,
        },
        "note": (
            "Weekly props stay gated. Replace frozen intercepts only if holdout "
            "MAE vs close and vs actual both improve with n>=80 per core market."
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
