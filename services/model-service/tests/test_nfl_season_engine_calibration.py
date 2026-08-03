"""Calibration helpers + sanity bounds for the hierarchical season engine."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_demo_universe,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.calibration import (
    CALIBRATION_TAG,
    GAME_SANITY,
    SEASON_SANITY,
    apply_efficiency_priors,
    efficiency_from_baseline_row,
    in_bounds,
    position_efficiency_defaults,
    with_residual_share,
)
from src.services.nfl_season_engine.types import PlayerRole


def test_engine_version_is_calibrated() -> None:
    # v1.1 *-calibrated; v1.2 injury; v1.3 deeper-usage; v1.4 survivor — cal tag persists.
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert CALIBRATION_TAG.startswith("nfl-season-engine-cal")
    assert any(
        tag in DEFAULT_SEASON_ENGINE_VERSION
        for tag in (
            "depth-volatility",
            "hardened",
            "survivor",
            "deeper-usage",
            "injury-shocks",
            "calibrated",
        )
    )


def test_residual_share_keeps_other_bucket() -> None:
    shares, other = with_residual_share([0.24, 0.16, 0.18, 0.10])
    assert abs(sum(shares) + other - 1.0) < 1e-9
    assert other >= 0.08
    # Sparse inflated shares get soft-normalized so other remains.
    shares2, other2 = with_residual_share([0.55, 0.45, 0.30])
    assert other2 >= 0.08
    assert sum(shares2) + other2 == 1.0 or abs(sum(shares2) + other2 - 1.0) < 1e-9


def test_position_efficiency_defaults_in_league_band() -> None:
    qb = position_efficiency_defaults("QB")
    assert 6.5 <= qb["ypa"] <= 7.8
    assert 0.012 <= qb["int_rate"] <= 0.025
    assert 0.03 <= qb["pass_td_rate"] <= 0.05
    rb = position_efficiency_defaults("RB")
    assert 3.5 <= rb["ypc"] <= 5.0
    assert 0.02 <= rb["rush_td_rate"] <= 0.04


def test_apply_efficiency_priors_and_baseline_derivation() -> None:
    role = PlayerRole(
        player_key="KC-QB1-Test",
        player_name="Test",
        team="KC",
        position="QB",
        source="unit",
    )
    calibrated = apply_efficiency_priors(role, overrides={"ypa": 7.4, "int_rate": 0.015})
    assert calibrated.ypa == 7.4
    assert calibrated.int_rate == 0.015
    assert "league_efficiency_v1" in calibrated.source

    derived = efficiency_from_baseline_row(
        {
            "attempts_mean": 34.0,
            "pass_yards_mean": 245.0,
            "pass_tds_mean": 1.4,
            "interceptions_mean": 0.55,
        },
        "QB",
    )
    assert abs(derived["ypa"] - (245.0 / 34.0)) < 1e-6
    assert abs(derived["int_rate"] - (0.55 / 34.0)) < 1e-6


def test_calibrated_buf_kc_game_boxes_in_sanity_bounds() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=200,
        seed=2026,
    )
    assert in_bounds(proj.game_script_summary["expected_total_mean"], "expected_total")

    mahomes = next(p for p in proj.players if "Mahomes" in p["player_name"])
    cook = next(p for p in proj.players if "Cook" in p["player_name"])
    rice = next(p for p in proj.players if "Rice" in p["player_name"])

    assert in_bounds(mahomes["point_estimate"]["pass_yards"], "qb_pass_yards")
    assert in_bounds(mahomes["point_estimate"]["pass_tds"], "qb_pass_tds")
    assert in_bounds(mahomes["point_estimate"]["ints"], "qb_ints")
    assert in_bounds(cook["point_estimate"]["rush_yards"], "rb1_rush_yards")
    assert in_bounds(rice["point_estimate"]["receptions"], "wr1_receptions")
    assert in_bounds(rice["point_estimate"]["rec_yards"], "wr1_rec_yards")

    # Distribution widths should be useful (not collapsed / not absurd).
    py = mahomes["distributions"]["pass_yards"]
    width = py["p90"] - py["p10"]
    assert 80.0 <= width <= 220.0
    assert py["std"] / max(1.0, py["mean"]) >= 0.12


def test_calibrated_season_totals_in_sanity_bounds() -> None:
    universe = build_demo_universe(2026)
    result = simulate_full_season(universe, n_sims=12, seed=9)
    assert abs(result.diagnostics["mean_wins_sum"] - 272.0) < 0.01
    assert result.diagnostics["win_mean_min"] >= GAME_SANITY["team_win_mean"][0]
    assert result.diagnostics["win_mean_max"] <= GAME_SANITY["team_win_mean"][1]
    # Contender-tier demo bumps should separate KC from a bottom club,
    # and the league win-mean stdev should not be pathologically compressed.
    kc = result.team_wins["KC"]["mean"]
    car = result.team_wins["CAR"]["mean"]
    assert kc > car + 1.5
    assert result.diagnostics["win_mean_stdev"] >= 1.1

    mahomes = next(r for r in result.player_season_totals if "Mahomes" in r["player_name"])
    cook = next(r for r in result.player_season_totals if "Cook" in r["player_name"])
    rice = next(r for r in result.player_season_totals if "Rice" in r["player_name"])

    assert SEASON_SANITY["qb_pass_yards"][0] <= mahomes["pass_yards_mean"] <= SEASON_SANITY["qb_pass_yards"][1]
    assert SEASON_SANITY["qb_ints"][0] <= mahomes["ints_mean"] <= SEASON_SANITY["qb_ints"][1]
    assert SEASON_SANITY["rb1_rush_yards"][0] <= cook["rush_yards_mean"] <= SEASON_SANITY["rb1_rush_yards"][1]
    assert SEASON_SANITY["wr1_rec_yards"][0] <= rice["rec_yards_mean"] <= SEASON_SANITY["wr1_rec_yards"][1]
    assert SEASON_SANITY["wr1_receptions"][0] <= rice["receptions_mean"] <= SEASON_SANITY["wr1_receptions"][1]
