#!/usr/bin/env python3
"""Retune NFL totals calibrator + market blend weights on owned closes.

DB-first. Uses nflverse spread_line/total_line as close substrate when
odds_snapshots open/close pairs are sparse. Writes before→after metrics to
data/ops/nfl-calibration-retune-*.json.

Does NOT call Odds API.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_simulator import (  # noqa: E402
    NFL_MARKET_BLEND_SPREAD_WEIGHT,
    NFL_MARKET_BLEND_TOTAL_WEIGHT,
    NflGameInputs,
    simulate_nfl_game,
)
from src.services.nfl_totals_calibration import _fit_linear_calibration  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "ops"
CANDIDATE_WEIGHTS = [0.0, 0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]


def _offense_defense_index(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    off_epa = float(off_epa or 0.0)
    def_epa_allowed = float(def_epa_allowed or 0.0)
    pressure_generated = float(pressure_generated or 0.0)
    pressure_allowed = float(pressure_allowed or 0.0)
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def _mae(preds: List[float], actuals: List[float]) -> float:
    return sum(abs(p - a) for p, a in zip(preds, actuals)) / len(actuals)


def main() -> int:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        n_sched = int(conn.execute(text("SELECT count(*) FROM nfl_dp_schedules")).scalar() or 0)
        if n_sched == 0:
            report = {
                "ok": False,
                "error": "nfl_dp_schedules empty — restore/ingest schedules before retune",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            path = OUT_DIR / "nfl-calibration-retune-blocked.json"
            path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
            return 2

        rows = conn.execute(
            text(
                """
                SELECT
                  sch.season, sch.week, sch.game_id, sch.home_team, sch.away_team,
                  sch.spread_line, sch.total_line, sch.home_score, sch.away_score,
                  hf.off_epa_per_play_5g AS home_off_epa,
                  hf.def_epa_allowed_per_play_5g AS home_def_epa,
                  hf.pressure_rate_generated_5g AS home_pressure_gen,
                  hf.pressure_rate_allowed_5g AS home_pressure_allowed,
                  hf.pass_rate_5g AS home_pass_rate,
                  hf.success_rate_offense_5g AS home_success_off,
                  hf.success_rate_defense_allowed_5g AS home_success_def,
                  af.off_epa_per_play_5g AS away_off_epa,
                  af.def_epa_allowed_per_play_5g AS away_def_epa,
                  af.pressure_rate_generated_5g AS away_pressure_gen,
                  af.pressure_rate_allowed_5g AS away_pressure_allowed,
                  af.pass_rate_5g AS away_pass_rate,
                  af.success_rate_offense_5g AS away_success_off,
                  af.success_rate_defense_allowed_5g AS away_success_def,
                  hk.kav_net_5g AS home_kav_net_5g,
                  ak.kav_net_5g AS away_kav_net_5g,
                  hk.kav_offense_5g AS home_kav_offense_5g,
                  ak.kav_offense_5g AS away_kav_offense_5g,
                  hk.kav_defense_5g AS home_kav_defense_5g,
                  ak.kav_defense_5g AS away_kav_defense_5g
                FROM nfl_dp_schedules sch
                LEFT JOIN nfl_dp_team_rolling_features_weekly hf
                  ON hf.season = sch.season AND hf.week = sch.week AND hf.team = sch.home_team
                LEFT JOIN nfl_dp_team_rolling_features_weekly af
                  ON af.season = sch.season AND af.week = sch.week AND af.team = sch.away_team
                LEFT JOIN nfl_dp_team_kav_weekly hk
                  ON hk.season = sch.season AND hk.week = (sch.week - 1) AND hk.team = sch.home_team
                LEFT JOIN nfl_dp_team_kav_weekly ak
                  ON ak.season = sch.season AND ak.week = (sch.week - 1) AND ak.team = sch.away_team
                WHERE sch.season BETWEEN 2023 AND 2025
                  AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
                  AND sch.spread_line IS NOT NULL AND sch.total_line IS NOT NULL
                  AND sch.week >= 2
                ORDER BY sch.season, sch.week, sch.game_id
                """
            )
        ).fetchall()

    components: List[Dict[str, Any]] = []
    for row in rows:
        m = dict(row._mapping)
        home_off_idx, home_def_idx = _offense_defense_index(
            m["home_off_epa"], m["home_def_epa"], m["home_pressure_gen"], m["home_pressure_allowed"]
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            m["away_off_epa"], m["away_def_epa"], m["away_pressure_gen"], m["away_pressure_allowed"]
        )
        # nflverse spread_line: + when home favored → Odds API market_spread_home = -spread_line
        market_spread_home = -float(m["spread_line"])
        market_total = float(m["total_line"])
        inputs = NflGameInputs(
            game_id=str(m["game_id"]),
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
            offense_index_home=home_off_idx,
            offense_index_away=away_off_idx,
            defense_index_home=home_def_idx,
            defense_index_away=away_def_idx,
            home_off_epa_5g=float(m["home_off_epa"]) if m["home_off_epa"] is not None else None,
            away_off_epa_5g=float(m["away_off_epa"]) if m["away_off_epa"] is not None else None,
            home_def_epa_allowed_5g=float(m["home_def_epa"]) if m["home_def_epa"] is not None else None,
            away_def_epa_allowed_5g=float(m["away_def_epa"]) if m["away_def_epa"] is not None else None,
            home_pass_rate_5g=float(m["home_pass_rate"]) if m["home_pass_rate"] is not None else None,
            away_pass_rate_5g=float(m["away_pass_rate"]) if m["away_pass_rate"] is not None else None,
            home_success_offense_5g=float(m["home_success_off"]) if m["home_success_off"] is not None else None,
            away_success_offense_5g=float(m["away_success_off"]) if m["away_success_off"] is not None else None,
            home_success_defense_allowed_5g=float(m["home_success_def"]) if m["home_success_def"] is not None else None,
            away_success_defense_allowed_5g=float(m["away_success_def"]) if m["away_success_def"] is not None else None,
            home_kav_net_5g=float(m["home_kav_net_5g"]) if m["home_kav_net_5g"] is not None else None,
            away_kav_net_5g=float(m["away_kav_net_5g"]) if m["away_kav_net_5g"] is not None else None,
            home_kav_offense_5g=float(m["home_kav_offense_5g"]) if m["home_kav_offense_5g"] is not None else None,
            away_kav_offense_5g=float(m["away_kav_offense_5g"]) if m["away_kav_offense_5g"] is not None else None,
            home_kav_defense_5g=float(m["home_kav_defense_5g"]) if m["home_kav_defense_5g"] is not None else None,
            away_kav_defense_5g=float(m["away_kav_defense_5g"]) if m["away_kav_defense_5g"] is not None else None,
            kav_as_of_week=int(m["week"]) - 1,
        )
        raw = simulate_nfl_game(
            inputs,
            simulations=800,
            seed=int(m["season"]) * 1000 + int(m["week"]),
            apply_linear_totals_calibration=False,
            market_spread_home=None,
            market_total=None,
        )
        markets = raw.get("markets") or {}
        components.append(
            {
                "season": int(m["season"]),
                "week": int(m["week"]),
                "raw_margin": -float(markets.get("spread_home") or 0.0),
                "raw_total": float(markets.get("total_mean") or 0.0),
                "market_margin": float(m["spread_line"]),
                "market_total": market_total,
                "actual_margin": float(m["home_score"]) - float(m["away_score"]),
                "actual_total": float(m["home_score"]) + float(m["away_score"]),
                "has_kav": m["home_kav_net_5g"] is not None and m["away_kav_net_5g"] is not None,
            }
        )

    # Split: tune on 2023-2024, holdout 2025
    tune = [c for c in components if c["season"] in (2023, 2024)]
    hold = [c for c in components if c["season"] == 2025]
    if not tune or not hold:
        print(json.dumps({"ok": False, "error": "insufficient tune/holdout rows", "n": len(components)}))
        return 2

    # Totals calibrator fit on tune
    cal_points = [
        {"pred_total": c["raw_total"], "actual_total": c["actual_total"], "days_ago": (2025 - c["season"]) * 365.0}
        for c in tune
    ]
    cal = _fit_linear_calibration(
        cal_points, min_sample_size=80, slope_min=0.75, slope_max=1.25, intercept_abs_max=8.0
    )

    def apply_cal(total: float) -> float:
        return float(cal["slope"]) * float(total) + float(cal["intercept"])

    # Blend sweep on tune
    def sweep(rows_in: List[Dict[str, Any]], spread_w: float, total_w: float, use_cal: bool) -> Dict[str, float]:
        spread_errs = []
        total_errs = []
        for c in rows_in:
            pred_margin = (1 - spread_w) * c["raw_margin"] + spread_w * c["market_margin"]
            pred_total = (1 - total_w) * c["raw_total"] + total_w * c["market_total"]
            if use_cal:
                pred_total = apply_cal(pred_total)
            spread_errs.append(abs(pred_margin - c["actual_margin"]))
            total_errs.append(abs(pred_total - c["actual_total"]))
        return {
            "spread_mae": round(sum(spread_errs) / len(spread_errs), 4),
            "total_mae": round(sum(total_errs) / len(total_errs), 4),
        }

    before_tune = sweep(tune, NFL_MARKET_BLEND_SPREAD_WEIGHT, NFL_MARKET_BLEND_TOTAL_WEIGHT, use_cal=False)
    before_hold = sweep(hold, NFL_MARKET_BLEND_SPREAD_WEIGHT, NFL_MARKET_BLEND_TOTAL_WEIGHT, use_cal=False)

    best = None
    for sw in CANDIDATE_WEIGHTS:
        for tw in CANDIDATE_WEIGHTS:
            m = sweep(tune, sw, tw, use_cal=True)
            score = m["spread_mae"] + m["total_mae"]
            cand = {"spread_w": sw, "total_w": tw, **m, "score": round(score, 4)}
            if best is None or cand["score"] < best["score"]:
                best = cand

    assert best is not None
    after_tune = sweep(tune, best["spread_w"], best["total_w"], use_cal=True)
    after_hold = sweep(hold, best["spread_w"], best["total_w"], use_cal=True)
    after_hold_uncal = sweep(hold, best["spread_w"], best["total_w"], use_cal=False)
    kav_n = sum(1 for c in components if c["has_kav"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": True,
        "n_components": len(components),
        "n_tune": len(tune),
        "n_holdout_2025": len(hold),
        "n_with_kav": kav_n,
        "before": {
            "blend_spread": NFL_MARKET_BLEND_SPREAD_WEIGHT,
            "blend_total": NFL_MARKET_BLEND_TOTAL_WEIGHT,
            "calibration": None,
            "tune": before_tune,
            "holdout_2025": before_hold,
        },
        "totals_calibrator": cal,
        "best_blend": best,
        "after": {
            "blend_spread": best["spread_w"],
            "blend_total": best["total_w"],
            "tune": after_tune,
            "holdout_2025_calibrated": after_hold,
            "holdout_2025_uncalibrated": after_hold_uncal,
        },
        "holdout_delta": {
            "spread_mae": round(after_hold["spread_mae"] - before_hold["spread_mae"], 4),
            "total_mae": round(after_hold["total_mae"] - before_hold["total_mae"], 4),
        },
        "recommendation": {
            "NFL_MARKET_BLEND_SPREAD_WEIGHT": best["spread_w"],
            "NFL_MARKET_BLEND_TOTAL_WEIGHT": best["total_w"],
            "totals_calibration_slope": cal.get("slope"),
            "totals_calibration_intercept": cal.get("intercept"),
            "totals_fit_mode": cal.get("fit_mode"),
            "promote_if_holdout_improves": bool(
                after_hold["spread_mae"] <= before_hold["spread_mae"]
                and after_hold["total_mae"] <= before_hold["total_mae"]
            ),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = OUT_DIR / f"nfl-calibration-retune-{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
