import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_simulator import DEFAULT_NFL_MODEL_VERSION, NflGameInputs, simulate_nfl_game


def test_simulate_nfl_game_returns_expected_market_fields() -> None:
    inputs = NflGameInputs(
        game_id="g1",
        home_team="Kansas City Chiefs",
        away_team="Buffalo Bills",
        offense_index_home=1.08,
        offense_index_away=1.04,
        defense_index_home=0.96,
        defense_index_away=0.98,
        rest_days_home=7.0,
        rest_days_away=6.0,
    )
    out = simulate_nfl_game(inputs, simulations=1200, seed=123)
    markets = out["markets"]
    assert 0.0 <= markets["home_win_prob"] <= 1.0
    assert 0.0 <= markets["away_win_prob"] <= 1.0
    assert markets["total_mean"] > 20.0
    assert isinstance(markets["fair_home_ml"], int)
    assert isinstance(markets["fair_away_ml"], int)


def test_simulate_nfl_game_uses_latest_default_model_version() -> None:
    inputs = NflGameInputs(
        game_id="g-default-version",
        home_team="New York Jets",
        away_team="Miami Dolphins",
    )
    out = simulate_nfl_game(inputs, simulations=400, seed=9)
    assert DEFAULT_NFL_MODEL_VERSION == "nfl-v1.5-matchup-sim"
    assert out["model_version"] == DEFAULT_NFL_MODEL_VERSION


def test_simulator_baseline_unchanged_without_matchup_features() -> None:
    inputs = NflGameInputs(
        game_id="g-no-pack",
        home_team="Baltimore Ravens",
        away_team="Cincinnati Bengals",
        offense_index_home=1.04,
        offense_index_away=1.01,
        defense_index_home=0.97,
        defense_index_away=1.03,
        rest_days_home=7.0,
        rest_days_away=7.0,
    )
    out = simulate_nfl_game(inputs, simulations=900, seed=7)
    matchup_diag = out["diagnostics"]["matchup_feature_adjustments"]
    assert matchup_diag["applied"] is False
    assert matchup_diag["home_points"] == 0.0
    assert matchup_diag["away_points"] == 0.0
    expected_home = 22.5 + 1.35 + 15.0 * ((1.04 / 1.03) - 1.0)
    expected_away = 21.0 + 15.0 * ((1.01 / 0.97) - 1.0)
    assert out["diagnostics"]["mean_home_points"] == round(expected_home, 3)
    assert out["diagnostics"]["mean_away_points"] == round(expected_away, 3)


def test_simulator_matchup_features_shift_projection_toward_home() -> None:
    baseline_inputs = NflGameInputs(
        game_id="g-pack",
        home_team="San Francisco 49ers",
        away_team="Seattle Seahawks",
        offense_index_home=1.01,
        offense_index_away=1.01,
        defense_index_home=0.99,
        defense_index_away=0.99,
        rest_days_home=7.0,
        rest_days_away=7.0,
    )
    feature_inputs = NflGameInputs(
        game_id="g-pack",
        home_team="San Francisco 49ers",
        away_team="Seattle Seahawks",
        offense_index_home=1.01,
        offense_index_away=1.01,
        defense_index_home=0.99,
        defense_index_away=0.99,
        rest_days_home=7.0,
        rest_days_away=7.0,
        matchup_diff_off_epa_5g=0.10,
        matchup_diff_def_epa_allowed_5g=0.08,
        matchup_diff_pressure_generated_5g=0.03,
        matchup_diff_pressure_allowed_5g=0.02,
        matchup_diff_red_zone_td_rate_5g=0.06,
        matchup_diff_success_rate_5g=0.05,
        home_off_epa_5g=0.11,
        away_off_epa_5g=0.03,
        home_pass_rate_5g=0.60,
        away_pass_rate_5g=0.58,
        feature_pack_version="nfl-v1-matchup-pack",
        matchup_season=2025,
        matchup_week=8,
    )
    baseline = simulate_nfl_game(baseline_inputs, simulations=2500, seed=19)
    with_features = simulate_nfl_game(feature_inputs, simulations=2500, seed=19)
    assert with_features["markets"]["home_win_prob"] > baseline["markets"]["home_win_prob"]
    assert with_features["markets"]["spread_home"] < baseline["markets"]["spread_home"]
    assert with_features["diagnostics"]["matchup_feature_adjustments"]["applied"] is True


def test_simulator_matchup_adjustments_are_clamped() -> None:
    extreme = NflGameInputs(
        game_id="g-pack-clamp",
        home_team="Dallas Cowboys",
        away_team="Philadelphia Eagles",
        offense_index_home=1.0,
        offense_index_away=1.0,
        defense_index_home=1.0,
        defense_index_away=1.0,
        matchup_diff_off_epa_5g=10.0,
        matchup_diff_def_epa_allowed_5g=10.0,
        matchup_diff_pressure_generated_5g=10.0,
        matchup_diff_pressure_allowed_5g=10.0,
        matchup_diff_red_zone_td_rate_5g=10.0,
        matchup_diff_success_rate_5g=10.0,
        home_off_epa_5g=10.0,
        away_off_epa_5g=10.0,
        home_pass_rate_5g=3.0,
        away_pass_rate_5g=3.0,
    )
    out = simulate_nfl_game(extreme, simulations=600, seed=101)
    adj = out["diagnostics"]["matchup_feature_adjustments"]
    assert adj["applied"] is True
    assert -3.6 <= adj["home_points"] <= 3.6
    assert -3.0 <= adj["away_points"] <= 3.0
    assert -4.25 <= adj["spread_signal"] <= 4.25
    assert -2.8 <= adj["total_signal"] <= 2.8


def test_simulator_totals_adjustments_and_calibration_are_reported() -> None:
    inputs = NflGameInputs(
        game_id="g-total-cal",
        home_team="Detroit Lions",
        away_team="Green Bay Packers",
        offense_index_home=1.03,
        offense_index_away=1.02,
        defense_index_home=0.99,
        defense_index_away=1.01,
        home_off_epa_5g=0.12,
        away_off_epa_5g=0.10,
        home_def_epa_allowed_5g=0.09,
        away_def_epa_allowed_5g=0.08,
        home_pass_rate_5g=0.63,
        away_pass_rate_5g=0.61,
        home_success_offense_5g=0.49,
        away_success_offense_5g=0.47,
        home_success_defense_allowed_5g=0.44,
        away_success_defense_allowed_5g=0.45,
        injury_nowcast_confidence_home=0.8,
        injury_nowcast_confidence_away=0.7,
        injury_nowcast_impact_home=0.3,
        injury_nowcast_impact_away=0.2,
        injury_nowcast_offense_multiplier_home=0.96,
        injury_nowcast_offense_multiplier_away=0.97,
        injury_nowcast_defense_multiplier_home=1.03,
        injury_nowcast_defense_multiplier_away=1.02,
    )
    out = simulate_nfl_game(
        inputs,
        simulations=1400,
        seed=44,
        totals_calibration={"slope": 0.92, "intercept": 1.4, "sample_size": 240, "source": "unit-test"},
    )
    totals_diag = out["diagnostics"]["totals_adjustments"]
    calibration_diag = out["diagnostics"]["totals_calibration"]
    assert totals_diag["applied"] is True
    assert abs(float(totals_diag["total_points"])) <= 4.2
    assert float(totals_diag["stdev_points"]) >= 0.0
    assert calibration_diag["source"] == "unit-test"
    assert calibration_diag["sample_size"] == 240
    assert calibration_diag["base_total"] != calibration_diag["calibrated_total"]


def test_simulator_totals_adjustments_fallback_without_signals() -> None:
    inputs = NflGameInputs(
        game_id="g-total-fallback",
        home_team="New York Giants",
        away_team="Washington Commanders",
    )
    out = simulate_nfl_game(inputs, simulations=800, seed=17)
    totals_diag = out["diagnostics"]["totals_adjustments"]
    calibration_diag = out["diagnostics"]["totals_calibration"]
    assert totals_diag["applied"] is False
    assert totals_diag["total_points"] == 0.0
    assert calibration_diag["source"] == "defaults"
