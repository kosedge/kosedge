"""Find the blend weights that actually hold up out-of-sample, with a strict
train/tune/test split so we don't fool ourselves:

  - Supervised ML model: trained on 2013-2023 (already excludes 2024-2025).
  - Tuning set: 2024 season (~285 games) -- sweep blend weights & trust-region
    clamps here only.
  - Final test set: 2025 season (~285 games) -- touched exactly once, at the
    end, with the winning config from the tuning set. This is the headline
    number that goes in the report.

Raw model components (heuristic sim mean margin/total, supervised model raw
predictions, market lines, actual outcomes) are computed once per game and
cached, so the weight sweep itself is pure arithmetic -- no re-simulation.
"""

from __future__ import annotations

import base64
import math
import os
import pickle
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

import numpy as np  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402
from src.services.nfl_supervised_retrain import FEATURE_KEYS, _build_matrix  # noqa: E402
from src.tasks import DEFAULT_NFL_MODEL_VERSION, _fetch_nfl_supervised_training_rows  # noqa: E402
from src.tasks import run_nfl_supervised_retrain  # noqa: E402

SIMULATIONS_PER_GAME = 1500
STDEV = 13.5


def _offense_defense_index(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    off_epa = float(off_epa or 0.0)
    def_epa_allowed = float(def_epa_allowed or 0.0)
    pressure_generated = float(pressure_generated or 0.0)
    pressure_allowed = float(pressure_allowed or 0.0)
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def _f(row, key):
    v = row.get(key)
    return float(v) if v is not None else None


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def compute_raw_components(session, rows, fit_payload):
    """Per game: heuristic-raw margin/total (no market blend), supervised
    raw predictions, market line, actual outcome. Computed once."""
    game_ids = [str(r["game_id"]) for r in rows]
    line_rows = session.execute(
        text("SELECT game_id, spread_line, total_line FROM nfl_dp_schedules WHERE game_id = ANY(:ids)"),
        {"ids": game_ids},
    ).fetchall()
    lines_by_game = {r.game_id: (float(r.spread_line), float(r.total_line)) for r in line_rows if r.spread_line is not None and r.total_line is not None}

    win_model = pickle.loads(base64.b64decode(fit_payload["models_pickle_b64"]["win"]))
    total_model = pickle.loads(base64.b64decode(fit_payload["models_pickle_b64"]["total"]))
    margin_model = pickle.loads(base64.b64decode(fit_payload["models_pickle_b64"]["margin"]))
    feature_keys = fit_payload["feature_keys"]

    feature_rows = []
    kept_rows = []
    for row in rows:
        game_id = str(row["game_id"])
        if game_id not in lines_by_game:
            continue
        feature_rows.append(
            {
                "week": _f(row, "week"),
                "home_off_epa_5g": _f(row, "home_off_epa_5g"),
                "away_off_epa_5g": _f(row, "away_off_epa_5g"),
                "home_def_epa_allowed_5g": _f(row, "home_def_epa_allowed_5g"),
                "away_def_epa_allowed_5g": _f(row, "away_def_epa_allowed_5g"),
                "home_pressure_allowed_5g": _f(row, "home_pressure_allowed_5g"),
                "away_pressure_allowed_5g": _f(row, "away_pressure_allowed_5g"),
                "home_pressure_generated_5g": _f(row, "home_pressure_generated_5g"),
                "away_pressure_generated_5g": _f(row, "away_pressure_generated_5g"),
                "home_pass_rate_5g": _f(row, "home_pass_rate_5g"),
                "away_pass_rate_5g": _f(row, "away_pass_rate_5g"),
                "home_early_down_pass_rate_5g": _f(row, "home_early_down_pass_rate_5g"),
                "away_early_down_pass_rate_5g": _f(row, "away_early_down_pass_rate_5g"),
                "home_red_zone_td_rate_5g": _f(row, "home_red_zone_td_rate_5g"),
                "away_red_zone_td_rate_5g": _f(row, "away_red_zone_td_rate_5g"),
                "home_success_offense_5g": _f(row, "home_success_offense_5g"),
                "away_success_offense_5g": _f(row, "away_success_offense_5g"),
                "home_success_defense_allowed_5g": _f(row, "home_success_defense_allowed_5g"),
                "away_success_defense_allowed_5g": _f(row, "away_success_defense_allowed_5g"),
                "diff_off_epa_5g": _f(row, "diff_off_epa_5g"),
                "diff_def_epa_allowed_5g": _f(row, "diff_def_epa_allowed_5g"),
                "diff_pressure_generated_5g": _f(row, "diff_pressure_generated_5g"),
                "diff_pressure_allowed_5g": _f(row, "diff_pressure_allowed_5g"),
                "diff_red_zone_td_rate_5g": _f(row, "diff_red_zone_td_rate_5g"),
                "diff_success_rate_5g": _f(row, "diff_success_rate_5g"),
                "home_injury_impact": _f(row, "home_injury_impact") or 0.0,
                "away_injury_impact": _f(row, "away_injury_impact") or 0.0,
                "diff_injury_impact": _f(row, "diff_injury_impact") or 0.0,
                "home_rest_days": _f(row, "home_rest_days") or 7.0,
                "away_rest_days": _f(row, "away_rest_days") or 7.0,
                "diff_rest_days": _f(row, "diff_rest_days") or 0.0,
                "roof_dome": _f(row, "roof_dome") or 0.0,
                "surface_turf": _f(row, "surface_turf") or 0.0,
                "is_divisional_game": _f(row, "is_divisional_game") or 0.0,
            }
        )
        kept_rows.append(row)

    x = _build_matrix(feature_rows, feature_keys)
    sup_home_prob = np.clip(win_model.predict_proba(x)[:, 1], 0.01, 0.99)
    sup_total_raw = np.clip(total_model.predict(x), 30.0, 66.0)
    sup_margin_raw = np.clip(margin_model.predict(x), -45.0, 45.0)

    components = []
    for i, row in enumerate(kept_rows):
        game_id = str(row["game_id"])
        market_spread_home, market_total = lines_by_game[game_id]

        home_off_idx, home_def_idx = _offense_defense_index(
            row.get("home_off_epa_5g"), row.get("home_def_epa_allowed_5g"),
            row.get("home_pressure_generated_5g"), row.get("home_pressure_allowed_5g"),
        )
        away_off_idx, away_def_idx = _offense_defense_index(
            row.get("away_off_epa_5g"), row.get("away_def_epa_allowed_5g"),
            row.get("away_pressure_generated_5g"), row.get("away_pressure_allowed_5g"),
        )
        inputs = NflGameInputs(
            game_id=game_id,
            home_team=str(row["home_team"]),
            away_team=str(row["away_team"]),
            offense_index_home=home_off_idx,
            offense_index_away=away_off_idx,
            defense_index_home=home_def_idx,
            defense_index_away=away_def_idx,
            rest_days_home=_f(row, "home_rest_days") or 7.0,
            rest_days_away=_f(row, "away_rest_days") or 7.0,
            matchup_season=int(row["season"]),
            matchup_week=int(row["week"]),
            matchup_game_id=game_id,
            matchup_home_team=str(row["home_team"]),
            matchup_away_team=str(row["away_team"]),
            home_off_epa_5g=_f(row, "home_off_epa_5g"),
            away_off_epa_5g=_f(row, "away_off_epa_5g"),
            home_def_epa_allowed_5g=_f(row, "home_def_epa_allowed_5g"),
            away_def_epa_allowed_5g=_f(row, "away_def_epa_allowed_5g"),
            home_pass_rate_5g=_f(row, "home_pass_rate_5g"),
            away_pass_rate_5g=_f(row, "away_pass_rate_5g"),
            home_success_offense_5g=_f(row, "home_success_offense_5g"),
            away_success_offense_5g=_f(row, "away_success_offense_5g"),
            home_success_defense_allowed_5g=_f(row, "home_success_defense_allowed_5g"),
            away_success_defense_allowed_5g=_f(row, "away_success_defense_allowed_5g"),
            matchup_diff_off_epa_5g=_f(row, "diff_off_epa_5g"),
            matchup_diff_def_epa_allowed_5g=_f(row, "diff_def_epa_allowed_5g"),
            matchup_diff_pressure_generated_5g=_f(row, "diff_pressure_generated_5g"),
            matchup_diff_pressure_allowed_5g=_f(row, "diff_pressure_allowed_5g"),
            matchup_diff_red_zone_td_rate_5g=_f(row, "diff_red_zone_td_rate_5g"),
            matchup_diff_success_rate_5g=_f(row, "diff_success_rate_5g"),
        )
        seed = abs(hash((game_id, "tune"))) % (2**31)

        heuristic_no_market = simulate_nfl_game(inputs, simulations=SIMULATIONS_PER_GAME, seed=seed)
        heuristic_raw_margin = -float(heuristic_no_market["markets"]["spread_home"])
        heuristic_raw_total = float(heuristic_no_market["markets"]["total_mean"])
        heuristic_raw_home_prob = float(heuristic_no_market["markets"]["home_win_prob"])

        heuristic_with_market = simulate_nfl_game(
            inputs, simulations=SIMULATIONS_PER_GAME, seed=seed,
            market_spread_home=market_spread_home, market_total=market_total,
        )
        mkt_blended_margin = -float(heuristic_with_market["markets"]["spread_home"])
        mkt_blended_total = float(heuristic_with_market["markets"]["total_mean"])
        mkt_blended_home_prob = float(heuristic_with_market["markets"]["home_win_prob"])

        components.append(
            {
                "season": int(row["season"]),
                "actual_margin": float(row["home_score"]) - float(row["away_score"]),
                "actual_total": float(row["home_score"]) + float(row["away_score"]),
                "actual_home_win": 1.0 if row["home_team_won"] else 0.0,
                "market_margin": market_spread_home,
                "market_total": market_total,
                "market_home_prob": _norm_cdf(market_spread_home / STDEV),
                "heuristic_raw_margin": heuristic_raw_margin,
                "heuristic_raw_total": heuristic_raw_total,
                "heuristic_raw_home_prob": heuristic_raw_home_prob,
                "mkt_blended_margin": mkt_blended_margin,
                "mkt_blended_total": mkt_blended_total,
                "mkt_blended_home_prob": mkt_blended_home_prob,
                "sup_margin_raw": float(sup_margin_raw[i]),
                "sup_total_raw": float(sup_total_raw[i]),
                "sup_home_prob": float(sup_home_prob[i]),
            }
        )
    return components


def evaluate_config(components, *, spread_weight, total_weight, home_win_weight, max_margin_dev, max_total_dev):
    margin_errs, total_errs, briers = [], [], []
    for c in components:
        base_margin = c["mkt_blended_margin"]
        base_total = c["mkt_blended_total"]
        base_home_prob = c["mkt_blended_home_prob"]

        sup_margin = float(np.clip(c["sup_margin_raw"], base_margin - max_margin_dev, base_margin + max_margin_dev))
        sup_total = float(np.clip(c["sup_total_raw"], base_total - max_total_dev, base_total + max_total_dev))

        blended_margin = ((1 - spread_weight) * base_margin) + (spread_weight * sup_margin)
        blended_total = ((1 - total_weight) * base_total) + (total_weight * sup_total)
        blended_home_prob = np.clip(((1 - home_win_weight) * base_home_prob) + (home_win_weight * c["sup_home_prob"]), 0.01, 0.99)

        margin_errs.append(abs(blended_margin - c["actual_margin"]))
        total_errs.append(abs(blended_total - c["actual_total"]))
        briers.append((blended_home_prob - c["actual_home_win"]) ** 2)
    return {
        "margin_mae": float(np.mean(margin_errs)),
        "total_mae": float(np.mean(total_errs)),
        "brier": float(np.mean(briers)),
    }


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Retraining supervised model on 2013-2023 only (2024-2025 fully held out)...")
    retrain_result = run_nfl_supervised_retrain.run(
        model_version=DEFAULT_NFL_MODEL_VERSION, start_season=2013, end_season=2023
    )
    print(f"Retrain metrics: {retrain_result['metrics']}")

    fit_row = session.execute(
        text(
            """
            SELECT payload FROM nfl_supervised_model_fits
            WHERE model_version = :mv AND train_start_season = 2013 AND train_end_season = 2023
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"mv": DEFAULT_NFL_MODEL_VERSION},
    ).fetchone()
    fit_payload = fit_row.payload

    all_rows = _fetch_nfl_supervised_training_rows(session, start_season=2024, end_season=2025)
    all_rows = [r for r in all_rows if r.get("home_team_won") is not None and r.get("final_total_points") is not None]
    tune_rows = [r for r in all_rows if int(r["season"]) == 2024]
    test_rows = [r for r in all_rows if int(r["season"]) == 2025]
    print(f"Tuning set (2024): {len(tune_rows)} games. Final test set (2025): {len(test_rows)} games.")

    print("Computing raw components for tuning set (2024)...")
    tune_components = compute_raw_components(session, tune_rows, fit_payload)
    print("Computing raw components for final test set (2025)...")
    test_components = compute_raw_components(session, test_rows, fit_payload)
    session.close()

    market_only_margin_mae_tune = float(np.mean([abs(c["market_margin"] - c["actual_margin"]) for c in tune_components]))
    market_only_total_mae_tune = float(np.mean([abs(c["market_total"] - c["actual_total"]) for c in tune_components]))
    print(f"\n[Tuning set 2024] Vegas margin MAE={market_only_margin_mae_tune:.3f} total MAE={market_only_total_mae_tune:.3f}")

    weight_grid = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    dev_grid = [3.0, 5.0, 7.0, 10.0, 14.0, 100.0]

    print("\nSweeping spread_weight x max_margin_dev on 2024 tuning set...")
    best_spread = None
    for w in weight_grid:
        for dev in dev_grid:
            res = evaluate_config(
                tune_components, spread_weight=w, total_weight=0.3, home_win_weight=0.4,
                max_margin_dev=dev, max_total_dev=6.0,
            )
            if best_spread is None or res["margin_mae"] < best_spread["margin_mae"]:
                best_spread = {**res, "spread_weight": w, "max_margin_dev": dev}
    print(f"Best spread config on 2024: weight={best_spread['spread_weight']} dev={best_spread['max_margin_dev']} -> MAE={best_spread['margin_mae']:.3f}")

    print("\nSweeping total_weight x max_total_dev on 2024 tuning set...")
    best_total = None
    for w in weight_grid:
        for dev in dev_grid:
            res = evaluate_config(
                tune_components, spread_weight=best_spread["spread_weight"], total_weight=w, home_win_weight=0.4,
                max_margin_dev=best_spread["max_margin_dev"], max_total_dev=dev,
            )
            if best_total is None or res["total_mae"] < best_total["total_mae"]:
                best_total = {**res, "total_weight": w, "max_total_dev": dev}
    print(f"Best total config on 2024: weight={best_total['total_weight']} dev={best_total['max_total_dev']} -> MAE={best_total['total_mae']:.3f}")

    print("\nSweeping home_win_weight on 2024 tuning set (Brier)...")
    best_win = None
    for w in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        res = evaluate_config(
            tune_components, spread_weight=best_spread["spread_weight"], total_weight=best_total["total_weight"],
            home_win_weight=w, max_margin_dev=best_spread["max_margin_dev"], max_total_dev=best_total["max_total_dev"],
        )
        if best_win is None or res["brier"] < best_win["brier"]:
            best_win = {**res, "home_win_weight": w}
    print(f"Best home_win_weight on 2024: weight={best_win['home_win_weight']} -> Brier={best_win['brier']:.4f}")

    final_config = {
        "spread_weight": best_spread["spread_weight"],
        "max_margin_dev": best_spread["max_margin_dev"],
        "total_weight": best_total["total_weight"],
        "max_total_dev": best_total["max_total_dev"],
        "home_win_weight": best_win["home_win_weight"],
    }
    print(f"\nFinal tuned config (chosen on 2024 only): {final_config}")

    print("\n" + "=" * 70)
    print("HEADLINE: applying tuned config to UNTOUCHED 2025 test set")
    print("=" * 70)
    old_config_result = evaluate_config(
        test_components, spread_weight=0.30, total_weight=0.30, home_win_weight=0.40,
        max_margin_dev=7.0, max_total_dev=6.0,
    )
    new_config_result = evaluate_config(test_components, spread_weight=final_config["spread_weight"], total_weight=final_config["total_weight"], home_win_weight=final_config["home_win_weight"], max_margin_dev=final_config["max_margin_dev"], max_total_dev=final_config["max_total_dev"])
    market_margin_mae_test = float(np.mean([abs(c["market_margin"] - c["actual_margin"]) for c in test_components]))
    market_total_mae_test = float(np.mean([abs(c["market_total"] - c["actual_total"]) for c in test_components]))
    market_brier_test = float(np.mean([(c["market_home_prob"] - c["actual_home_win"]) ** 2 for c in test_components]))

    print(f"{'Metric':<20}{'Old config':>14}{'Tuned config':>14}{'Vegas':>12}")
    print(f"{'Margin MAE':<20}{old_config_result['margin_mae']:>14.3f}{new_config_result['margin_mae']:>14.3f}{market_margin_mae_test:>12.3f}")
    print(f"{'Total MAE':<20}{old_config_result['total_mae']:>14.3f}{new_config_result['total_mae']:>14.3f}{market_total_mae_test:>12.3f}")
    print(f"{'Brier':<20}{old_config_result['brier']:>14.4f}{new_config_result['brier']:>14.4f}{market_brier_test:>12.4f}")

    # Bootstrap significance of tuned-config vs Vegas on the untouched test set
    rng = np.random.default_rng(11)
    margin_diffs = np.array(
        [abs((( 1 - final_config["spread_weight"]) * c["mkt_blended_margin"] + final_config["spread_weight"] * np.clip(c["sup_margin_raw"], c["mkt_blended_margin"] - final_config["max_margin_dev"], c["mkt_blended_margin"] + final_config["max_margin_dev"])) - c["actual_margin"]) - abs(c["market_margin"] - c["actual_margin"]) for c in test_components]
    )
    n_boot = 5000
    boot_means = np.array([np.mean(margin_diffs[rng.integers(0, len(margin_diffs), len(margin_diffs))]) for _ in range(n_boot)])
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    print(f"\nSpread MAE diff (tuned - vegas) on 2025 test: {np.mean(margin_diffs):+.3f}, 95% CI [{lo:+.3f}, {hi:+.3f}] "
          f"{'SIGNIFICANT' if hi < 0 or lo > 0 else 'not significant'}")

    print("\n" + "=" * 70)
    print("OUTLIER / TAIL-RISK CHECK (production robustness, not just average MAE)")
    print("=" * 70)
    for label, cfg in [
        ("Tuned (no clamp)", final_config),
        ("Conservative (dev=14, weight=0.85)", {**final_config, "spread_weight": 0.85, "max_margin_dev": 14.0}),
        ("Conservative (dev=10, weight=0.85)", {**final_config, "spread_weight": 0.85, "max_margin_dev": 10.0}),
        ("Old default (0.30/dev=7)", {"spread_weight": 0.30, "max_margin_dev": 7.0, "total_weight": 0.30, "max_total_dev": 6.0, "home_win_weight": 0.40}),
    ]:
        errs = []
        for c in test_components:
            base_margin = c["mkt_blended_margin"]
            sup_margin = float(np.clip(c["sup_margin_raw"], base_margin - cfg["max_margin_dev"], base_margin + cfg["max_margin_dev"]))
            blended = ((1 - cfg["spread_weight"]) * base_margin) + (cfg["spread_weight"] * sup_margin)
            errs.append(abs(blended - c["actual_margin"]))
        errs = np.array(errs)
        print(f"{label:<38} MAE={errs.mean():.3f}  P90={np.percentile(errs, 90):.2f}  P99={np.percentile(errs, 99):.2f}  Max={errs.max():.2f}")


if __name__ == "__main__":
    main()
