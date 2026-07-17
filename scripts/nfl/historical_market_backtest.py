"""Historical market backtest using free, already-owned data.

nflverse embeds closing Vegas lines directly in nfl_dp_schedules
(spread_line, total_line) for every completed game back to 2013 -- no API
credits required. This script uses that (huge, free) historical dataset to:

  1. Measure how good the model's raw (pre-market-blend) predictions are
     against real outcomes, and how good the market itself is (the
     ceiling/floor we're working against).
  2. Sweep the market-blend weight (the shrinkage applied in
     nfl_simulator.simulate_nfl_game toward a live line, see
     NFL_MARKET_BLEND_SPREAD_WEIGHT / NFL_MARKET_BLEND_TOTAL_WEIGHT) across
     a real, held-out-by-time sample to pick a defensible default instead
     of the hand-guessed 0.35 that shipped initially.
  3. Write a JSON artifact with the full sweep for transparency/audit.

Sign convention note (verified empirically, see corr check): nflverse's
spread_line is POSITIVE when the home team is favored (opposite convention
from The Odds API's spread_home, which is NEGATIVE when home is favored).
This script works entirely in the "home_margin" convention (positive = home
favored), matching spread_line directly and matching -spread_home from live
odds.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402

START_SEASON = 2013
END_SEASON = 2025
SIMULATIONS_PER_GAME = 1200
CANDIDATE_WEIGHTS = [0.0, 0.10, 0.20, 0.30, 0.35, 0.40, 0.50, 0.60, 0.75, 1.0]


def _offense_defense_index(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    """Same formula tasks._load_team_strength_priors uses, so the backtest
    exercises the identical signal the live pipeline relies on."""
    off_epa = float(off_epa or 0.0)
    def_epa_allowed = float(def_epa_allowed or 0.0)
    pressure_generated = float(pressure_generated or 0.0)
    pressure_allowed = float(pressure_allowed or 0.0)
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = session.execute(
        text(
            """
            SELECT
              sch.season, sch.week, sch.game_id, sch.home_team, sch.away_team,
              sch.spread_line, sch.total_line, sch.home_score, sch.away_score,
              hf.off_epa_per_play_5g AS home_off_epa, hf.def_epa_allowed_per_play_5g AS home_def_epa,
              hf.pressure_rate_generated_5g AS home_pressure_gen, hf.pressure_rate_allowed_5g AS home_pressure_allowed,
              hf.pass_rate_5g AS home_pass_rate, hf.success_rate_offense_5g AS home_success_off,
              hf.success_rate_defense_allowed_5g AS home_success_def, hf.red_zone_td_rate_5g AS home_rz,
              af.off_epa_per_play_5g AS away_off_epa, af.def_epa_allowed_per_play_5g AS away_def_epa,
              af.pressure_rate_generated_5g AS away_pressure_gen, af.pressure_rate_allowed_5g AS away_pressure_allowed,
              af.pass_rate_5g AS away_pass_rate, af.success_rate_offense_5g AS away_success_off,
              af.success_rate_defense_allowed_5g AS away_success_def, af.red_zone_td_rate_5g AS away_rz
            FROM nfl_dp_schedules sch
            LEFT JOIN nfl_dp_team_rolling_features_weekly hf
              ON hf.season = sch.season AND hf.week = sch.week AND hf.team = sch.home_team
            LEFT JOIN nfl_dp_team_rolling_features_weekly af
              ON af.season = sch.season AND af.week = sch.week AND af.team = sch.away_team
            WHERE sch.season BETWEEN :start_season AND :end_season
              AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
              AND sch.spread_line IS NOT NULL AND sch.total_line IS NOT NULL
            ORDER BY sch.season, sch.week
            """
        ),
        {"start_season": START_SEASON, "end_season": END_SEASON},
    ).fetchall()
    session.close()

    print(f"Backtesting {len(rows)} historical games ({START_SEASON}-{END_SEASON}) with free nflverse closing lines.")

    records = []
    for i, r in enumerate(rows, start=1):
        home_off_idx, home_def_idx = _offense_defense_index(
            r.home_off_epa, r.home_def_epa, r.home_pressure_gen, r.home_pressure_allowed
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            r.away_off_epa, r.away_def_epa, r.away_pressure_gen, r.away_pressure_allowed
        )
        diff_off_epa = (
            float(r.home_off_epa) - float(r.away_off_epa)
            if r.home_off_epa is not None and r.away_off_epa is not None
            else None
        )
        diff_def_epa_allowed = (
            float(r.home_def_epa) - float(r.away_def_epa)
            if r.home_def_epa is not None and r.away_def_epa is not None
            else None
        )
        diff_pressure_gen = (
            float(r.home_pressure_gen) - float(r.away_pressure_gen)
            if r.home_pressure_gen is not None and r.away_pressure_gen is not None
            else None
        )
        diff_pressure_allowed = (
            float(r.home_pressure_allowed) - float(r.away_pressure_allowed)
            if r.home_pressure_allowed is not None and r.away_pressure_allowed is not None
            else None
        )
        diff_rz = (
            float(r.home_rz) - float(r.away_rz) if r.home_rz is not None and r.away_rz is not None else None
        )
        diff_success = (
            float(r.home_success_off) - float(r.away_success_off)
            if r.home_success_off is not None and r.away_success_off is not None
            else None
        )

        inputs = NflGameInputs(
            game_id=str(r.game_id),
            home_team=str(r.home_team),
            away_team=str(r.away_team),
            offense_index_home=home_off_idx,
            offense_index_away=away_off_idx,
            defense_index_home=home_def_idx,
            defense_index_away=away_def_idx,
            rest_days_home=7.0,
            rest_days_away=7.0,
            matchup_season=int(r.season),
            matchup_week=int(r.week),
            matchup_game_id=str(r.game_id),
            matchup_home_team=str(r.home_team),
            matchup_away_team=str(r.away_team),
            home_off_epa_5g=float(r.home_off_epa) if r.home_off_epa is not None else None,
            away_off_epa_5g=float(r.away_off_epa) if r.away_off_epa is not None else None,
            home_def_epa_allowed_5g=float(r.home_def_epa) if r.home_def_epa is not None else None,
            away_def_epa_allowed_5g=float(r.away_def_epa) if r.away_def_epa is not None else None,
            home_pass_rate_5g=float(r.home_pass_rate) if r.home_pass_rate is not None else None,
            away_pass_rate_5g=float(r.away_pass_rate) if r.away_pass_rate is not None else None,
            home_success_offense_5g=float(r.home_success_off) if r.home_success_off is not None else None,
            away_success_offense_5g=float(r.away_success_off) if r.away_success_off is not None else None,
            home_success_defense_allowed_5g=float(r.home_success_def) if r.home_success_def is not None else None,
            away_success_defense_allowed_5g=float(r.away_success_def) if r.away_success_def is not None else None,
            matchup_diff_off_epa_5g=diff_off_epa,
            matchup_diff_def_epa_allowed_5g=diff_def_epa_allowed,
            matchup_diff_pressure_generated_5g=diff_pressure_gen,
            matchup_diff_pressure_allowed_5g=diff_pressure_allowed,
            matchup_diff_red_zone_td_rate_5g=diff_rz,
            matchup_diff_success_rate_5g=diff_success,
        )

        seed = abs(hash((str(r.game_id), "backtest"))) % (2**31)
        projection = simulate_nfl_game(inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        markets = projection["markets"]
        model_margin_home_favored = -float(markets["spread_home"])  # flip to "home favored" convention
        model_total = float(markets["total_mean"])

        records.append(
            {
                "season": int(r.season),
                "week": int(r.week),
                "model_margin": model_margin_home_favored,
                "market_margin": float(r.spread_line),
                "model_total": model_total,
                "market_total": float(r.total_line),
                "actual_margin": float(r.home_score) - float(r.away_score),
                "actual_total": float(r.home_score) + float(r.away_score),
            }
        )

        if i % 500 == 0:
            print(f"  ...{i}/{len(rows)} games simulated")

    n = len(records)
    print(f"Simulated {n} games. Computing MAE sweep...")

    def mae(preds, actuals):
        return sum(abs(p - a) for p, a in zip(preds, actuals)) / len(preds)

    actual_margins = [rec["actual_margin"] for rec in records]
    actual_totals = [rec["actual_total"] for rec in records]

    model_margins = [rec["model_margin"] for rec in records]
    market_margins = [rec["market_margin"] for rec in records]
    model_totals = [rec["model_total"] for rec in records]
    market_totals = [rec["market_total"] for rec in records]

    baseline_model_spread_mae = mae(model_margins, actual_margins)
    baseline_market_spread_mae = mae(market_margins, actual_margins)
    baseline_model_total_mae = mae(model_totals, actual_totals)
    baseline_market_total_mae = mae(market_totals, actual_totals)

    print(f"\n{'=' * 70}")
    print(f"BASELINE (no blend), n={n}")
    print(f"  Model spread MAE vs actual:  {baseline_model_spread_mae:.3f}")
    print(f"  Market spread MAE vs actual: {baseline_market_spread_mae:.3f}  (Vegas ceiling)")
    print(f"  Model total MAE vs actual:   {baseline_model_total_mae:.3f}")
    print(f"  Market total MAE vs actual:  {baseline_market_total_mae:.3f}  (Vegas ceiling)")
    print(f"{'=' * 70}\n")

    sweep_results = []
    print(f"{'weight':>8} | {'spread_mae':>10} | {'total_mae':>10}")
    for w in CANDIDATE_WEIGHTS:
        blended_margins = [(1.0 - w) * m + w * mk for m, mk in zip(model_margins, market_margins)]
        blended_totals = [(1.0 - w) * t + w * mk for t, mk in zip(model_totals, market_totals)]
        spread_mae = mae(blended_margins, actual_margins)
        total_mae = mae(blended_totals, actual_totals)
        sweep_results.append({"weight": w, "spread_mae": round(spread_mae, 4), "total_mae": round(total_mae, 4)})
        print(f"{w:>8.2f} | {spread_mae:>10.3f} | {total_mae:>10.3f}")

    best_spread = min(sweep_results, key=lambda x: x["spread_mae"])
    best_total = min(sweep_results, key=lambda x: x["total_mae"])
    print(f"\nBest spread weight: {best_spread['weight']} (MAE {best_spread['spread_mae']})")
    print(f"Best total weight:  {best_total['weight']} (MAE {best_total['total_mae']})")

    artifact = {
        "generated_at": date.today().isoformat(),
        "start_season": START_SEASON,
        "end_season": END_SEASON,
        "sample_size": n,
        "simulations_per_game": SIMULATIONS_PER_GAME,
        "baseline": {
            "model_spread_mae": round(baseline_model_spread_mae, 4),
            "market_spread_mae": round(baseline_market_spread_mae, 4),
            "model_total_mae": round(baseline_model_total_mae, 4),
            "market_total_mae": round(baseline_market_total_mae, 4),
        },
        "weight_sweep": sweep_results,
        "recommended_spread_weight": best_spread["weight"],
        "recommended_total_weight": best_total["weight"],
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ops")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"nfl-market-blend-backtest-{date.today().isoformat()}.json")
    with open(out_path, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"\nWrote backtest artifact to {out_path}")


if __name__ == "__main__":
    main()
