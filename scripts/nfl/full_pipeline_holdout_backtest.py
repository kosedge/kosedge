"""The real test: does the FULL production pipeline (heuristic Monte Carlo
decomposition + live market-line blend + supervised gradient-boosted overlay)
beat Vegas closing lines on games it has never seen?

This reuses the exact same chronological train/test split the supervised
model already uses (last ~16% of 2013-2025 by season/week, which lands on
2024-2025 -- 570 games) so there is zero leakage: those games were excluded
from training the active nfl_supervised_model_fits row.

For each held-out game, this runs the identical code path production uses:
  1. simulate_nfl_game() with market_spread_home/market_total set from
     nflverse's free closing spread_line/total_line (this is what a live
     odds_snapshots pull would have supplied), producing base_markets.
  2. apply_supervised_blend() on top, using the currently-active fit.
The result is compared against the actual outcome AND against the market
line itself, on the same games, with a paired significance test (not just a
point-estimate MAE, which can be noise over ~570 games).
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

import numpy as np  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402
from src.services.nfl_supervised_retrain import apply_supervised_blend  # noqa: E402
from src.tasks import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    _fetch_nfl_supervised_training_rows,
)

MODEL_VERSION = DEFAULT_NFL_MODEL_VERSION
HOLDOUT_FRACTION = 0.16
SIMULATIONS_PER_GAME = 1500
N_BOOTSTRAP = 5000


def _offense_defense_index(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    off_epa = float(off_epa or 0.0)
    def_epa_allowed = float(def_epa_allowed or 0.0)
    pressure_generated = float(pressure_generated or 0.0)
    pressure_allowed = float(pressure_allowed or 0.0)
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def bootstrap_mae_diff_ci(errors_a, errors_b, n_boot=N_BOOTSTRAP, seed=7):
    """Paired bootstrap CI for mean(errors_a) - mean(errors_b). If the CI
    excludes 0, the difference is statistically meaningful, not noise."""
    rng = np.random.default_rng(seed)
    a = np.asarray(errors_a)
    b = np.asarray(errors_b)
    n = len(a)
    diffs = a - b
    point = float(np.mean(diffs))
    boot_means = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_means[i] = np.mean(diffs[idx])
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    return point, float(lo), float(hi)


def brier(preds, actuals):
    p = np.asarray(preds)
    a = np.asarray(actuals)
    return float(np.mean((p - a) ** 2))


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    fit_row = session.execute(
        text(
            """
            SELECT payload, train_start_season, train_end_season, test_rows, metrics
            FROM nfl_supervised_model_fits
            WHERE model_version = :model_version AND is_active = true
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"model_version": MODEL_VERSION},
    ).fetchone()
    if fit_row is None:
        raise SystemExit("No active supervised fit found -- run run_nfl_supervised_retrain first.")

    fit_payload = fit_row.payload
    print(
        f"Using active supervised fit trained {fit_row.train_start_season}-{fit_row.train_end_season}, "
        f"own internal test_rows={fit_row.test_rows}, own test metrics={fit_row.metrics}"
    )

    training_rows = _fetch_nfl_supervised_training_rows(
        session, start_season=int(fit_row.train_start_season), end_season=int(fit_row.train_end_season)
    )
    usable = [
        r for r in training_rows if r.get("home_team_won") is not None and r.get("final_total_points") is not None
    ]
    usable = sorted(
        usable,
        key=lambda row: (
            float(row.get("season") or 0.0),
            float(row.get("week") or 0.0),
            str(row.get("game_id") or ""),
        ),
    )
    holdout_size = int(round(len(usable) * HOLDOUT_FRACTION))
    holdout_size = max(120, holdout_size)
    holdout_size = min(holdout_size, len(usable) - 120)
    holdout_rows = usable[-holdout_size:]
    print(f"Holdout: {len(holdout_rows)} games, {holdout_rows[0]['season']} wk{holdout_rows[0]['week']} "
          f"through {holdout_rows[-1]['season']} wk{holdout_rows[-1]['week']}")

    game_ids = [str(r["game_id"]) for r in holdout_rows]
    line_rows = session.execute(
        text(
            """
            SELECT game_id, spread_line, total_line
            FROM nfl_dp_schedules
            WHERE game_id = ANY(:game_ids)
            """
        ),
        {"game_ids": game_ids},
    ).fetchall()
    lines_by_game = {r.game_id: (float(r.spread_line), float(r.total_line)) for r in line_rows if r.spread_line is not None and r.total_line is not None}
    session.close()

    model_margin_errs, model_total_errs, model_home_probs = [], [], []
    market_margin_errs, market_total_errs, market_home_probs = [], [], []
    actual_home_wins = []
    heuristic_only_margin_errs, heuristic_only_total_errs = [], []

    skipped = 0
    for row in holdout_rows:
        game_id = str(row["game_id"])
        lines = lines_by_game.get(game_id)
        if lines is None:
            skipped += 1
            continue
        market_spread_home, market_total = lines

        home_off_idx, home_def_idx = _offense_defense_index(
            row.get("home_off_epa_5g"), row.get("home_def_epa_allowed_5g"),
            row.get("home_pressure_generated_5g"), row.get("home_pressure_allowed_5g"),
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            row.get("away_off_epa_5g"), row.get("away_def_epa_allowed_5g"),
            row.get("away_pressure_generated_5g"), row.get("away_pressure_allowed_5g"),
        )

        def _f(key):
            v = row.get(key)
            return float(v) if v is not None else None

        inputs = NflGameInputs(
            game_id=game_id,
            home_team=str(row["home_team"]),
            away_team=str(row["away_team"]),
            offense_index_home=home_off_idx,
            offense_index_away=away_off_idx,
            defense_index_home=home_def_idx,
            defense_index_away=away_def_idx,
            rest_days_home=_f("home_rest_days") or 7.0,
            rest_days_away=_f("away_rest_days") or 7.0,
            matchup_season=int(row["season"]),
            matchup_week=int(row["week"]),
            matchup_game_id=game_id,
            matchup_home_team=str(row["home_team"]),
            matchup_away_team=str(row["away_team"]),
            home_off_epa_5g=_f("home_off_epa_5g"),
            away_off_epa_5g=_f("away_off_epa_5g"),
            home_def_epa_allowed_5g=_f("home_def_epa_allowed_5g"),
            away_def_epa_allowed_5g=_f("away_def_epa_allowed_5g"),
            home_pass_rate_5g=_f("home_pass_rate_5g"),
            away_pass_rate_5g=_f("away_pass_rate_5g"),
            home_success_offense_5g=_f("home_success_offense_5g"),
            away_success_offense_5g=_f("away_success_offense_5g"),
            home_success_defense_allowed_5g=_f("home_success_defense_allowed_5g"),
            away_success_defense_allowed_5g=_f("away_success_defense_allowed_5g"),
            matchup_diff_off_epa_5g=_f("diff_off_epa_5g"),
            matchup_diff_def_epa_allowed_5g=_f("diff_def_epa_allowed_5g"),
            matchup_diff_pressure_generated_5g=_f("diff_pressure_generated_5g"),
            matchup_diff_pressure_allowed_5g=_f("diff_pressure_allowed_5g"),
            matchup_diff_red_zone_td_rate_5g=_f("diff_red_zone_td_rate_5g"),
            matchup_diff_success_rate_5g=_f("diff_success_rate_5g"),
        )

        seed = abs(hash((game_id, "holdout-full-pipeline"))) % (2**31)

        heuristic_only = simulate_nfl_game(inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        heuristic_only_margin_errs.append(
            abs(-float(heuristic_only["markets"]["spread_home"]) - (float(row["home_score"]) - float(row["away_score"])))
        )
        heuristic_only_total_errs.append(
            abs(float(heuristic_only["markets"]["total_mean"]) - (float(row["home_score"]) + float(row["away_score"])))
        )

        projection = simulate_nfl_game(
            inputs,
            simulations=SIMULATIONS_PER_GAME,
            seed=seed,
            market_spread_home=market_spread_home,
            market_total=market_total,
        )
        base_markets = projection["markets"]

        feature_row = {
            "week": _f("week"),
            "home_off_epa_5g": _f("home_off_epa_5g"),
            "away_off_epa_5g": _f("away_off_epa_5g"),
            "home_def_epa_allowed_5g": _f("home_def_epa_allowed_5g"),
            "away_def_epa_allowed_5g": _f("away_def_epa_allowed_5g"),
            "home_pressure_allowed_5g": _f("home_pressure_allowed_5g"),
            "away_pressure_allowed_5g": _f("away_pressure_allowed_5g"),
            "home_pressure_generated_5g": _f("home_pressure_generated_5g"),
            "away_pressure_generated_5g": _f("away_pressure_generated_5g"),
            "home_pass_rate_5g": _f("home_pass_rate_5g"),
            "away_pass_rate_5g": _f("away_pass_rate_5g"),
            "home_early_down_pass_rate_5g": _f("home_early_down_pass_rate_5g"),
            "away_early_down_pass_rate_5g": _f("away_early_down_pass_rate_5g"),
            "home_red_zone_td_rate_5g": _f("home_red_zone_td_rate_5g"),
            "away_red_zone_td_rate_5g": _f("away_red_zone_td_rate_5g"),
            "home_success_offense_5g": _f("home_success_offense_5g"),
            "away_success_offense_5g": _f("away_success_offense_5g"),
            "home_success_defense_allowed_5g": _f("home_success_defense_allowed_5g"),
            "away_success_defense_allowed_5g": _f("away_success_defense_allowed_5g"),
            "diff_off_epa_5g": _f("diff_off_epa_5g"),
            "diff_def_epa_allowed_5g": _f("diff_def_epa_allowed_5g"),
            "diff_pressure_generated_5g": _f("diff_pressure_generated_5g"),
            "diff_pressure_allowed_5g": _f("diff_pressure_allowed_5g"),
            "diff_red_zone_td_rate_5g": _f("diff_red_zone_td_rate_5g"),
            "diff_success_rate_5g": _f("diff_success_rate_5g"),
            "home_injury_impact": _f("home_injury_impact") or 0.0,
            "away_injury_impact": _f("away_injury_impact") or 0.0,
            "diff_injury_impact": _f("diff_injury_impact") or 0.0,
            "home_rest_days": _f("home_rest_days") or 7.0,
            "away_rest_days": _f("away_rest_days") or 7.0,
            "diff_rest_days": _f("diff_rest_days") or 0.0,
            "roof_dome": _f("roof_dome") or 0.0,
            "surface_turf": _f("surface_turf") or 0.0,
            "is_divisional_game": _f("is_divisional_game") or 0.0,
        }

        blended = apply_supervised_blend(fit_payload=fit_payload, feature_row=feature_row, base_markets=base_markets)

        actual_margin = float(row["home_score"]) - float(row["away_score"])
        actual_total = float(row["home_score"]) + float(row["away_score"])
        actual_home_win = 1.0 if row["home_team_won"] else 0.0

        model_margin_errs.append(abs(-float(blended["spread_home"]) - actual_margin))
        model_total_errs.append(abs(float(blended["total_mean"]) - actual_total))
        model_home_probs.append(float(blended["home_win_prob"]))

        market_margin_errs.append(abs(market_spread_home - actual_margin))
        market_total_errs.append(abs(market_total - actual_total))
        STDEV = 13.5
        market_home_prob = 0.5 * (1 + math.erf((market_spread_home / STDEV) / math.sqrt(2)))
        market_home_probs.append(market_home_prob)
        actual_home_wins.append(actual_home_win)

    n = len(model_margin_errs)
    print(f"\nEvaluated {n} games (skipped {skipped} without lines).\n")

    print("=" * 78)
    print(f"{'Metric':<28} {'Heuristic-only':>14} {'Full pipeline':>14} {'Vegas':>10}")
    print("=" * 78)
    print(
        f"{'Margin/Spread MAE':<28} {np.mean(heuristic_only_margin_errs):>14.3f} "
        f"{np.mean(model_margin_errs):>14.3f} {np.mean(market_margin_errs):>10.3f}"
    )
    print(
        f"{'Total MAE':<28} {np.mean(heuristic_only_total_errs):>14.3f} "
        f"{np.mean(model_total_errs):>14.3f} {np.mean(market_total_errs):>10.3f}"
    )
    print(
        f"{'Win-prob Brier':<28} {'':>14} "
        f"{brier(model_home_probs, actual_home_wins):>14.4f} {brier(market_home_probs, actual_home_wins):>10.4f}"
    )
    print("=" * 78)

    spread_point, spread_lo, spread_hi = bootstrap_mae_diff_ci(model_margin_errs, market_margin_errs)
    total_point, total_lo, total_hi = bootstrap_mae_diff_ci(model_total_errs, market_total_errs)

    print(f"\nPaired bootstrap 95% CI, (full-pipeline MAE - Vegas MAE), negative = model better, n_boot={N_BOOTSTRAP}:")
    print(f"  Spread: {spread_point:+.3f}  95% CI [{spread_lo:+.3f}, {spread_hi:+.3f}]"
          f"  {'SIGNIFICANT' if spread_hi < 0 or spread_lo > 0 else 'not significant (CI includes 0)'}")
    print(f"  Total:  {total_point:+.3f}  95% CI [{total_lo:+.3f}, {total_hi:+.3f}]"
          f"  {'SIGNIFICANT' if total_hi < 0 or total_lo > 0 else 'not significant (CI includes 0)'}")

    win_rate_model_closer_spread = float(np.mean(np.array(model_margin_errs) < np.array(market_margin_errs)))
    win_rate_model_closer_total = float(np.mean(np.array(model_total_errs) < np.array(market_total_errs)))
    print(f"\nPer-game win rate (model closer to actual than Vegas):")
    print(f"  Spread: {win_rate_model_closer_spread:.1%}  Total: {win_rate_model_closer_total:.1%}")


if __name__ == "__main__":
    main()
