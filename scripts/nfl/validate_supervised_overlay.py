"""Honest out-of-sample validation of the supervised gradient-boosting
overlay: uses the SAME chronological holdout that fit_nfl_supervised_models
actually trained on (the model never saw these games), builds the exact
enriched feature rows from tasks._fetch_nfl_supervised_training_rows, runs
the raw simulator, then the simulator+supervised blend, and compares both
against the free nflverse closing lines and actual outcomes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402
from src.services.nfl_supervised_retrain import apply_supervised_blend  # noqa: E402
from src.tasks import (  # noqa: E402
    _fetch_nfl_supervised_training_rows,
    _load_latest_supervised_fit,
)

START_SEASON = 2013
END_SEASON = 2025
HOLDOUT_FRACTION = 0.16
SIMULATIONS_PER_GAME = 1200


def _f(value):
    """Decimal-safe float coercion -- psycopg returns numeric columns as
    decimal.Decimal, which doesn't support arithmetic with plain floats."""
    if value is None:
        return None
    return float(value)


def _offense_defense_index(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    off_epa = _f(off_epa) or 0.0
    def_epa_allowed = _f(def_epa_allowed) or 0.0
    pressure_generated = _f(pressure_generated) or 0.0
    pressure_allowed = _f(pressure_allowed) or 0.0
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    fit_payload = _load_latest_supervised_fit(session, model_version="nfl-v1.5-matchup-sim")
    if fit_payload is None:
        print("No trained supervised fit found -- run run_nfl_supervised_retrain first.")
        return

    rows = _fetch_nfl_supervised_training_rows(session, start_season=START_SEASON, end_season=END_SEASON)
    rows = sorted(rows, key=lambda r: (float(r.get("season") or 0), float(r.get("week") or 0), str(r.get("game_id") or "")))
    holdout_size = max(120, int(round(len(rows) * HOLDOUT_FRACTION)))
    holdout_size = min(holdout_size, len(rows) - 120)
    test_rows = rows[-holdout_size:]

    # Pull market lines for exactly these held-out games.
    game_ids = [str(r["game_id"]) for r in test_rows]
    market_rows = session.execute(
        text(
            "SELECT game_id, spread_line, total_line FROM nfl_dp_schedules WHERE game_id = ANY(:ids)"
        ),
        {"ids": game_ids},
    ).fetchall()
    market_by_game = {r.game_id: r for r in market_rows}
    session.close()

    print(f"Validating on {len(test_rows)} held-out games (never seen by the trained model).")

    records = []
    for i, row in enumerate(test_rows, start=1):
        market_row = market_by_game.get(str(row["game_id"]))
        if market_row is None or market_row.spread_line is None or market_row.total_line is None:
            continue

        home_off_idx, home_def_idx = _offense_defense_index(
            row.get("home_off_epa_5g"), row.get("home_def_epa_allowed_5g"),
            row.get("home_pressure_generated_5g"), row.get("home_pressure_allowed_5g"),
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            row.get("away_off_epa_5g"), row.get("away_def_epa_allowed_5g"),
            row.get("away_pressure_generated_5g"), row.get("away_pressure_allowed_5g"),
        )

        inputs = NflGameInputs(
            game_id=str(row["game_id"]),
            home_team=str(row["home_team"]),
            away_team=str(row["away_team"]),
            offense_index_home=home_off_idx,
            offense_index_away=away_off_idx,
            defense_index_home=home_def_idx,
            defense_index_away=away_def_idx,
            rest_days_home=float(row.get("home_rest_days") or 7.0),
            rest_days_away=float(row.get("away_rest_days") or 7.0),
            matchup_season=int(row["season"]),
            matchup_week=int(row["week"]),
            matchup_game_id=str(row["game_id"]),
            matchup_home_team=str(row["home_team"]),
            matchup_away_team=str(row["away_team"]),
            home_off_epa_5g=_f(row.get("home_off_epa_5g")),
            away_off_epa_5g=_f(row.get("away_off_epa_5g")),
            home_def_epa_allowed_5g=_f(row.get("home_def_epa_allowed_5g")),
            away_def_epa_allowed_5g=_f(row.get("away_def_epa_allowed_5g")),
            home_pass_rate_5g=_f(row.get("home_pass_rate_5g")),
            away_pass_rate_5g=_f(row.get("away_pass_rate_5g")),
            home_success_offense_5g=_f(row.get("home_success_offense_5g")),
            away_success_offense_5g=_f(row.get("away_success_offense_5g")),
            home_success_defense_allowed_5g=_f(row.get("home_success_defense_allowed_5g")),
            away_success_defense_allowed_5g=_f(row.get("away_success_defense_allowed_5g")),
            matchup_diff_off_epa_5g=_f(row.get("diff_off_epa_5g")),
            matchup_diff_def_epa_allowed_5g=_f(row.get("diff_def_epa_allowed_5g")),
            matchup_diff_pressure_generated_5g=_f(row.get("diff_pressure_generated_5g")),
            matchup_diff_pressure_allowed_5g=_f(row.get("diff_pressure_allowed_5g")),
            matchup_diff_red_zone_td_rate_5g=_f(row.get("diff_red_zone_td_rate_5g")),
            matchup_diff_success_rate_5g=_f(row.get("diff_success_rate_5g")),
        )
        seed = abs(hash((str(row["game_id"]), "validate-supervised"))) % (2**31)
        projection = simulate_nfl_game(inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        raw_markets = projection["markets"]

        blended_markets = apply_supervised_blend(fit_payload=fit_payload, feature_row=row, base_markets=raw_markets)
        overlay = blended_markets.get("supervised_overlay") or {}

        actual_margin = float(row["home_score"]) - float(row["away_score"])
        actual_total = float(row["home_score"]) + float(row["away_score"])
        actual_home_win = 1.0 if actual_margin > 0 else 0.0

        records.append(
            {
                "raw_margin": -float(raw_markets["spread_home"]),
                "blend_margin": -float(blended_markets["spread_home"]),
                "sup_margin": -float(overlay.get("supervised_spread_home", raw_markets["spread_home"])),
                "market_margin": float(market_row.spread_line),
                "raw_total": float(raw_markets["total_mean"]),
                "blend_total": float(blended_markets["total_mean"]),
                "sup_total": float(overlay.get("supervised_total_mean", raw_markets["total_mean"])),
                "market_total": float(market_row.total_line),
                "raw_home_prob": float(raw_markets["home_win_prob"]),
                "blend_home_prob": float(blended_markets["home_win_prob"]),
                "sup_home_prob": float(overlay.get("supervised_home_prob", raw_markets["home_win_prob"])),
                "actual_margin": actual_margin,
                "actual_total": actual_total,
                "actual_home_win": actual_home_win,
            }
        )
        if i % 200 == 0:
            print(f"  ...{i}/{len(test_rows)}")

    n = len(records)

    def mae(key_pred, key_actual="actual_margin"):
        return sum(abs(r[key_pred] - r[key_actual]) for r in records) / n

    def brier(key_pred):
        return sum((r[key_pred] - r["actual_home_win"]) ** 2 for r in records) / n

    def mae_generic(preds, actuals):
        return sum(abs(p - a) for p, a in zip(preds, actuals)) / len(preds)

    def brier_generic(preds, actuals):
        return sum((p - a) ** 2 for p, a in zip(preds, actuals)) / len(preds)

    print(f"\n{'=' * 78}")
    print(f"OUT-OF-SAMPLE VALIDATION (n={n} held-out games the model never trained on)")
    print(f"{'=' * 78}")
    print(f"{'Metric':<28} {'Raw sim':>10} {'+Supervised':>12} {'Market':>10}")
    print(
        f"{'Spread MAE (vs actual)':<28} {mae('raw_margin'):>10.3f} {mae('blend_margin'):>12.3f} "
        f"{mae('market_margin'):>10.3f}"
    )
    print(
        f"{'Total MAE (vs actual)':<28} {mae('raw_total','actual_total'):>10.3f} "
        f"{mae('blend_total','actual_total'):>12.3f} {mae('market_total','actual_total'):>10.3f}"
    )
    print(f"{'Win Brier (vs actual)':<28} {brier('raw_home_prob'):>10.4f} {brier('blend_home_prob'):>12.4f} {'n/a':>10}")
    print(f"{'=' * 78}")

    market_margins = [r["market_margin"] for r in records]
    market_totals = [r["market_total"] for r in records]
    raw_vs_market_spread = sum(abs(r["raw_margin"] - m) for r, m in zip(records, market_margins)) / n
    blend_vs_market_spread = sum(abs(r["blend_margin"] - m) for r, m in zip(records, market_margins)) / n
    raw_vs_market_total = sum(abs(r["raw_total"] - m) for r, m in zip(records, market_totals)) / n
    blend_vs_market_total = sum(abs(r["blend_total"] - m) for r, m in zip(records, market_totals)) / n
    print(f"\nAgreement with market (lower = closer to Vegas, not necessarily better):")
    print(f"  Raw spread vs market:      {raw_vs_market_spread:.3f}")
    print(f"  Blended spread vs market:  {blend_vs_market_spread:.3f}")
    print(f"  Raw total vs market:       {raw_vs_market_total:.3f}")
    print(f"  Blended total vs market:   {blend_vs_market_total:.3f}")

    print(f"\n{'=' * 60}\nBLEND WEIGHT SWEEP (raw_sim <-weight-> supervised_pred)\n{'=' * 60}")
    print(f"{'weight':>8} | {'spread_mae':>10} | {'total_mae':>10} | {'win_brier':>10}")
    best_spread = (0.0, float("inf"))
    best_total = (0.0, float("inf"))
    best_brier = (0.0, float("inf"))
    for w in [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        s_mae = mae_generic(
            [(1 - w) * r["raw_margin"] + w * r["sup_margin"] for r in records],
            [r["actual_margin"] for r in records],
        )
        t_mae = mae_generic(
            [(1 - w) * r["raw_total"] + w * r["sup_total"] for r in records],
            [r["actual_total"] for r in records],
        )
        b = brier_generic(
            [(1 - w) * r["raw_home_prob"] + w * r["sup_home_prob"] for r in records],
            [r["actual_home_win"] for r in records],
        )
        if s_mae < best_spread[1]:
            best_spread = (w, s_mae)
        if t_mae < best_total[1]:
            best_total = (w, t_mae)
        if b < best_brier[1]:
            best_brier = (w, b)
        print(f"{w:>8.2f} | {s_mae:>10.3f} | {t_mae:>10.3f} | {b:>10.4f}")
    print(f"\nBest spread weight: {best_spread[0]} (MAE {best_spread[1]:.3f})")
    print(f"Best total weight:  {best_total[0]} (MAE {best_total[1]:.3f})")
    print(f"Best win weight:    {best_brier[0]} (Brier {best_brier[1]:.4f})")


if __name__ == "__main__":
    main()
