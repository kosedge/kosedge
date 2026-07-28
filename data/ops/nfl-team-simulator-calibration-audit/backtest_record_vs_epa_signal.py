"""Real backtest: does the RECORD-based team-strength signal that actually
drives live production (tasks.py::run_nfl_market_simulations's
offense_home/defense_home selection, which prefers ESPN win-loss record over
the EPA-based rolling-feature prior whenever a non-degenerate record exists)
perform as well as the EPA-based signal that scripts/nfl/historical_market_backtest.py
actually validated?

No leakage: each team's win-loss record entering week W is computed from that
team's own real games in weeks < W, this season only (matches
team_strength_from_record's real-world input: ESPN's live win-loss summary
at kickoff, never including the game being predicted).
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_data import team_strength_from_record  # noqa: E402
from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402

START_SEASON = 2023
END_SEASON = 2025
SIMULATIONS_PER_GAME = 1200


def _offense_defense_index_epa(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
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
              af.off_epa_per_play_5g AS away_off_epa, af.def_epa_allowed_per_play_5g AS away_def_epa,
              af.pressure_rate_generated_5g AS away_pressure_gen, af.pressure_rate_allowed_5g AS away_pressure_allowed
            FROM nfl_dp_schedules sch
            LEFT JOIN nfl_dp_team_rolling_features_weekly hf
              ON hf.season = sch.season AND hf.week = sch.week AND hf.team = sch.home_team
            LEFT JOIN nfl_dp_team_rolling_features_weekly af
              ON af.season = sch.season AND af.week = sch.week AND af.team = sch.away_team
            WHERE sch.season BETWEEN :start_season AND :end_season
              AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
              AND sch.spread_line IS NOT NULL AND sch.total_line IS NOT NULL
            ORDER BY sch.season, sch.week, sch.game_id
            """
        ),
        {"start_season": START_SEASON, "end_season": END_SEASON},
    ).fetchall()
    session.close()

    print(f"Backtesting {len(rows)} real games ({START_SEASON}-{END_SEASON}).")

    # Real cumulative win-loss record per (season, team), no leakage: updated
    # AFTER simulating each game, using that game's real final score.
    record: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])  # [wins, losses]

    def_records = []
    epa_records = []
    for i, r in enumerate(rows, start=1):
        season = int(r.season)
        home_key = (season, str(r.home_team))
        away_key = (season, str(r.away_team))
        home_wl = record[home_key]
        away_wl = record[away_key]
        home_record_summary = f"{home_wl[0]}-{home_wl[1]}"
        away_record_summary = f"{away_wl[0]}-{away_wl[1]}"

        rec_off_home, rec_def_home = team_strength_from_record(home_record_summary)
        rec_off_away, rec_def_away = team_strength_from_record(away_record_summary)

        epa_off_home, epa_def_home = _offense_defense_index_epa(
            r.home_off_epa, r.home_def_epa, r.home_pressure_gen, r.home_pressure_allowed
        )
        epa_off_away, epa_def_away = _offense_defense_index_epa(
            r.away_off_epa, r.away_def_epa, r.away_pressure_gen, r.away_pressure_allowed
        )

        seed = abs(hash((str(r.game_id), "record-vs-epa-backtest"))) % (2**31)

        rec_inputs = NflGameInputs(
            game_id=str(r.game_id),
            home_team=str(r.home_team),
            away_team=str(r.away_team),
            offense_index_home=rec_off_home,
            offense_index_away=rec_off_away,
            defense_index_home=rec_def_home,
            defense_index_away=rec_def_away,
            rest_days_home=7.0,
            rest_days_away=7.0,
        )
        rec_projection = simulate_nfl_game(rec_inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        rec_markets = rec_projection["markets"]

        epa_inputs = NflGameInputs(
            game_id=str(r.game_id),
            home_team=str(r.home_team),
            away_team=str(r.away_team),
            offense_index_home=epa_off_home,
            offense_index_away=epa_off_away,
            defense_index_home=epa_def_home,
            defense_index_away=epa_def_away,
            rest_days_home=7.0,
            rest_days_away=7.0,
        )
        epa_projection = simulate_nfl_game(epa_inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        epa_markets = epa_projection["markets"]

        actual_margin = float(r.home_score) - float(r.away_score)
        actual_total = float(r.home_score) + float(r.away_score)

        def_records.append(
            {
                "season": season,
                "week": int(r.week),
                "home_record_entering": home_record_summary,
                "away_record_entering": away_record_summary,
                "model_margin": -float(rec_markets["spread_home"]),
                "model_total": float(rec_markets["total_mean"]),
                "market_margin": float(r.spread_line),
                "market_total": float(r.total_line),
                "actual_margin": actual_margin,
                "actual_total": actual_total,
            }
        )
        epa_records.append(
            {
                "season": season,
                "week": int(r.week),
                "model_margin": -float(epa_markets["spread_home"]),
                "model_total": float(epa_markets["total_mean"]),
                "market_margin": float(r.spread_line),
                "market_total": float(r.total_line),
                "actual_margin": actual_margin,
                "actual_total": actual_total,
            }
        )

        # Update AFTER simulating (real record entering the game, not leaking this result).
        if r.home_score > r.away_score:
            home_wl[0] += 1
            away_wl[1] += 1
        elif r.away_score > r.home_score:
            away_wl[0] += 1
            home_wl[1] += 1
        else:
            pass  # tie: real NFL rule is 0.5 win each; ignored here, rare (~1-2/season)

        if i % 500 == 0:
            print(f"  ...{i}/{len(rows)} games simulated")

    def mae(preds, actuals):
        return sum(abs(p - a) for p, a in zip(preds, actuals)) / len(preds)

    def bias(preds, actuals):
        return sum(p - a for p, a in zip(preds, actuals)) / len(preds)

    def corr(a, b):
        n = len(a)
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / n
        var_a = sum((x - mean_a) ** 2 for x in a) / n
        var_b = sum((y - mean_b) ** 2 for y in b) / n
        if var_a <= 0 or var_b <= 0:
            return 0.0
        return cov / ((var_a**0.5) * (var_b**0.5))

    all_seasons = sorted({rec["season"] for rec in def_records})
    print(f"\n{'=' * 90}")
    print("Overall, ALL WEEKS (includes week-1 degenerate 0-0 records, which fall back to EPA prior anyway):")
    for name, records in (("RECORD-based (live production signal)", def_records), ("EPA-based (validated backtest signal)", epa_records)):
        model_margins = [x["model_margin"] for x in records]
        actual_margins = [x["actual_margin"] for x in records]
        model_totals = [x["model_total"] for x in records]
        actual_totals = [x["actual_total"] for x in records]
        market_margins = [x["market_margin"] for x in records]
        market_totals = [x["market_total"] for x in records]
        print(f"\n  {name} (n={len(records)}):")
        print(f"    spread MAE vs actual: {mae(model_margins, actual_margins):.3f}  (bias {bias(model_margins, actual_margins):+.3f})")
        print(f"    total  MAE vs actual: {mae(model_totals, actual_totals):.3f}  (bias {bias(model_totals, actual_totals):+.3f})")
        print(f"    spread corr vs actual: {corr(model_margins, actual_margins):.4f}   (market: {corr(market_margins, actual_margins):.4f})")
        print(f"    total  corr vs actual: {corr(model_totals, actual_totals):.4f}   (market: {corr(market_totals, actual_totals):.4f})")

    print(f"\n{'=' * 90}")
    print("RESTRICTED to week >= 4 (real, non-degenerate in-season record on both sides -- the actual live steady-state case):")
    def_records_w4 = [x for x in def_records if x["week"] >= 4]
    epa_records_w4 = [x for x in epa_records if x["week"] >= 4]
    for name, records in (("RECORD-based (live production signal)", def_records_w4), ("EPA-based (validated backtest signal)", epa_records_w4)):
        model_margins = [x["model_margin"] for x in records]
        actual_margins = [x["actual_margin"] for x in records]
        model_totals = [x["model_total"] for x in records]
        actual_totals = [x["actual_total"] for x in records]
        market_margins = [x["market_margin"] for x in records]
        market_totals = [x["market_total"] for x in records]
        print(f"\n  {name} (n={len(records)}):")
        print(f"    spread MAE vs actual: {mae(model_margins, actual_margins):.3f}  (bias {bias(model_margins, actual_margins):+.3f})")
        print(f"    total  MAE vs actual: {mae(model_totals, actual_totals):.3f}  (bias {bias(model_totals, actual_totals):+.3f})")
        print(f"    spread corr vs actual: {corr(model_margins, actual_margins):.4f}   (market: {corr(market_margins, actual_margins):.4f})")
        print(f"    total  corr vs actual: {corr(model_totals, actual_totals):.4f}   (market: {corr(market_totals, actual_totals):.4f})")

    market_margins_all = [x["market_margin"] for x in def_records]
    market_totals_all = [x["market_total"] for x in def_records]
    actual_margins_all = [x["actual_margin"] for x in def_records]
    actual_totals_all = [x["actual_total"] for x in def_records]
    print(f"\n{'=' * 90}")
    print("Market ceiling (all weeks):")
    print(f"    spread MAE vs actual: {mae(market_margins_all, actual_margins_all):.3f}")
    print(f"    total  MAE vs actual: {mae(market_totals_all, actual_totals_all):.3f}")

    out_path = os.path.join(os.path.dirname(__file__), "record_vs_epa_backtest_records.json")
    with open(out_path, "w") as f:
        json.dump({"record_signal": def_records, "epa_signal": epa_records}, f)
    print(f"\nWrote raw records to {out_path}")


if __name__ == "__main__":
    main()
