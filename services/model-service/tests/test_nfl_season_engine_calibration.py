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
    early_season_uncertainty,
    efficiency_from_baseline_row,
    in_bounds,
    matchup_response_for_week,
    position_efficiency_defaults,
    score_noise_sd_for_week,
    share_vol_mult_for_week,
    win_prob_margin_sd_for_week,
    with_residual_share,
)
from src.services.nfl_season_engine.team_strength import (
    expected_team_points,
    win_prob_from_expected_scores,
)
from src.services.nfl_season_engine.types import PlayerRole, TeamStrengthState


def test_engine_version_is_calibrated() -> None:
    # cal-v2 tag remains; engine version tracks latest capability (v1.13+).
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "calibration" in DEFAULT_SEASON_ENGINE_VERSION
        or "player-regression" in DEFAULT_SEASON_ENGINE_VERSION
        or "projected-sos" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor-planner" in DEFAULT_SEASON_ENGINE_VERSION
    )
    assert CALIBRATION_TAG.startswith("nfl-season-engine-cal")
    assert CALIBRATION_TAG.endswith("v2") or "v2" in CALIBRATION_TAG


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
    te = position_efficiency_defaults("TE")
    assert te["ypr"] <= position_efficiency_defaults("WR")["ypr"]
    assert te["rec_td_rate"] >= 0.05


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
    assert "league_efficiency_v2" in calibrated.source or "league_efficiency" in calibrated.source

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


def test_early_season_uncertainty_posture() -> None:
    w1 = early_season_uncertainty(1)
    w5 = early_season_uncertainty(5)
    assert w1["active"] is True
    assert w5["active"] is False
    assert score_noise_sd_for_week(1) > score_noise_sd_for_week(5)
    assert win_prob_margin_sd_for_week(1) > win_prob_margin_sd_for_week(10)
    assert matchup_response_for_week(1) < matchup_response_for_week(10)
    assert share_vol_mult_for_week(1) > share_vol_mult_for_week(10)
    # Softened early separation → closer win probs for the same strength gap.
    elite = TeamStrengthState(team="A", offense_index=1.18, defense_index=1.12)
    dog = TeamStrengthState(team="B", offense_index=0.88, defense_index=0.90)
    h1 = expected_team_points(elite, dog, home=True, week=1)
    a1 = expected_team_points(dog, elite, home=False, week=1)
    h10 = expected_team_points(elite, dog, home=True, week=10)
    a10 = expected_team_points(dog, elite, home=False, week=10)
    assert abs(h1 - a1) < abs(h10 - a10)
    wp1 = win_prob_from_expected_scores(h1, a1, week=1)
    wp10 = win_prob_from_expected_scores(h10, a10, week=10)
    assert abs(wp1 - 0.5) < abs(wp10 - 0.5)


def test_calibrated_buf_kc_game_boxes_in_sanity_bounds() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=200,
        seed=2026,
        include_diagnostics=True,
    )
    assert in_bounds(proj.game_script_summary["expected_total_mean"], "expected_total")
    assert "early_season_uncertainty" in proj.diagnostics
    assert proj.diagnostics["early_season_uncertainty"]["active"] is True

    mahomes = next(p for p in proj.players if "Mahomes" in p["player_name"])
    cook = next(p for p in proj.players if "Cook" in p["player_name"])
    rice = next(p for p in proj.players if "Rice" in p["player_name"])

    assert in_bounds(mahomes["point_estimate"]["pass_yards"], "qb_pass_yards")
    assert in_bounds(mahomes["point_estimate"]["pass_tds"], "qb_pass_tds")
    assert in_bounds(mahomes["point_estimate"]["ints"], "qb_ints")
    assert in_bounds(cook["point_estimate"]["rush_yards"], "rb1_rush_yards")
    assert in_bounds(rice["point_estimate"]["receptions"], "wr1_receptions")
    assert in_bounds(rice["point_estimate"]["rec_yards"], "wr1_rec_yards")
    # Guard against reintroducing WR/RB inflation from sparse-roster renormalize.
    assert cook["point_estimate"]["rush_yards"] < 95.0
    assert rice["point_estimate"]["rec_yards"] < 100.0

    # Distribution widths should be useful (not collapsed / not absurd).
    py = mahomes["distributions"]["pass_yards"]
    width = py["p90"] - py["p10"]
    assert 80.0 <= width <= 220.0
    assert py["std"] / max(1.0, py["mean"]) >= 0.12


def test_real_depth_qb1_not_starved_by_backup_snap_priors() -> None:
    """Real depth lists QB2/QB3 snaps; QB1 must still own attempts when healthy."""
    from src.services.nfl_season_engine import build_packaged_real_universe

    universe = build_packaged_real_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=120,
        seed=2026,
    )
    mahomes = next(p for p in proj.players if "Mahomes" in p["player_name"])
    att = mahomes["distributions"]["pass_attempts"]["mean"]
    assert att >= 32.0
    assert in_bounds(mahomes["point_estimate"]["pass_yards"], "qb_pass_yards")
    assert mahomes["point_estimate"]["pass_yards"] >= 200.0


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
    assert result.diagnostics["win_mean_stdev"] >= 1.2
    assert result.diagnostics["win_mean_spread"] >= 5.0
    assert "early_season_uncertainty" in result.diagnostics
    assert result.diagnostics["early_season_uncertainty"]["by_week"]["1"]["active"] is True

    mahomes = next(r for r in result.player_season_totals if "Mahomes" in r["player_name"])
    cook = next(r for r in result.player_season_totals if "Cook" in r["player_name"])
    rice = next(r for r in result.player_season_totals if "Rice" in r["player_name"])

    assert SEASON_SANITY["qb_pass_yards"][0] <= mahomes["pass_yards_mean"] <= SEASON_SANITY["qb_pass_yards"][1]
    assert SEASON_SANITY["qb_ints"][0] <= mahomes["ints_mean"] <= SEASON_SANITY["qb_ints"][1]
    assert SEASON_SANITY["qb_pass_tds"][0] <= mahomes["pass_tds_mean"] <= SEASON_SANITY["qb_pass_tds"][1]
    assert SEASON_SANITY["rb1_rush_yards"][0] <= cook["rush_yards_mean"] <= SEASON_SANITY["rb1_rush_yards"][1]
    assert SEASON_SANITY["wr1_rec_yards"][0] <= rice["rec_yards_mean"] <= SEASON_SANITY["wr1_rec_yards"][1]
    assert SEASON_SANITY["wr1_receptions"][0] <= rice["receptions_mean"] <= SEASON_SANITY["wr1_receptions"][1]
