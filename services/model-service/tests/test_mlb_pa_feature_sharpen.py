from src.services.mlb_lineup_shock import apply_lineup_shock
from src.services.mlb_pa_feature_sharpen import (
    apply_missing_pitcher_shrink,
    bullpen_quality_from_state,
    compute_sp_change_shock,
    platoon_split_for_hand,
    rest_day_multipliers,
    sharpen_game_inputs,
    starter_firmness,
    weather_reliability_mul,
)
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game


def test_missing_pitcher_has_low_firmness() -> None:
    assert starter_firmness(starter_name=None) <= 0.45
    assert starter_firmness(starter_name="Ace Pitcher", starter_source="mlb-stats-api") >= 0.85


def test_missing_pitcher_shrink_pulls_toward_one() -> None:
    shrunk = apply_missing_pitcher_shrink(1.20, firmness=0.40)
    assert 1.0 < shrunk < 1.20


def test_rest_day_multipliers_bounded() -> None:
    short = rest_day_multipliers(0.0)
    long = rest_day_multipliers(4.0)
    assert 0.97 <= short["offense_mul"] <= 1.0
    assert long["offense_mul"] >= 1.0
    assert -0.06 <= short["bullpen_stress"] <= 0.08


def test_bullpen_quality_from_state_moves_with_fatigue() -> None:
    fresh = bullpen_quality_from_state(fatigue=0.30, availability=0.85, high_lev_availability=0.80)
    tired = bullpen_quality_from_state(fatigue=0.85, availability=0.35, high_lev_availability=0.30)
    assert fresh > tired
    assert 0.82 <= tired <= 1.18


def test_dome_weather_reliability_damped() -> None:
    assert weather_reliability_mul(home_abbr="TOR", weather_temp_f=72.0) < 0.5
    assert weather_reliability_mul(home_abbr="NYY", weather_temp_f=72.0, weather_wind_mph=8.0) == 1.0
    assert 0.6 <= weather_reliability_mul(home_abbr="NYY", weather_temp_f=72.0) < 1.0


def test_sp_change_shock_detects_change() -> None:
    shock = compute_sp_change_shock(
        prior_starter="Old Starter",
        new_starter="New Ace",
        prior_quality=1.10,
        new_quality=0.92,
    )
    assert shock["changed"] == 1.0
    assert shock["allowed_mul"] < 1.0


def test_sharpen_and_lineup_shock_bounded() -> None:
    base = MlbGameInputs(
        game_id="g-sharpen",
        home_team="Yankees",
        away_team="Red Sox",
        starter_home=None,
        starter_away="Named Starter",
        starter_quality_home=1.15,
        offense_home=1.05,
        offense_split_home=1.10,
        bullpen_fatigue_home=0.80,
        bullpen_availability_home=0.40,
        park_factor_runs=1.03,
        weather_temp_f=78.0,
    )
    sharpened, diag = sharpen_game_inputs(
        base,
        starter_source_home="neutral",
        starter_source_away="mlb-stats-api",
        home_abbr="NYY",
        rest_days_home=0.0,
        rest_days_away=1.0,
    )
    assert "pa_feature_sharpen" in diag
    assert sharpened.starter_firmness_home < sharpened.starter_firmness_away
    assert 0.78 <= sharpened.offense_home <= 1.25
    shocked, shock_diag = apply_lineup_shock(
        sharpened,
        prior_confidence_home=0.50,
        prior_confidence_away=0.85,
        prior_starter_home="Old Guy",
        prior_starter_away="Named Starter",
        prior_starter_quality_home=1.0,
        prior_starter_quality_away=1.0,
    )
    assert "sp_change_shock" in shock_diag
    assert 0.78 <= shocked.offense_home <= 1.25


def test_platoon_split_for_hand_picks_matchup_index() -> None:
    assert platoon_split_for_hand(
        season_index=1.0,
        split_vs_l=1.08,
        split_vs_r=0.96,
        opponent_hand="L",
    ) == 1.08
    assert platoon_split_for_hand(
        season_index=1.0,
        split_vs_l=1.08,
        split_vs_r=0.96,
        opponent_hand="R",
    ) == 0.96
    assert platoon_split_for_hand(
        season_index=1.02,
        split_vs_l=None,
        split_vs_r=None,
        opponent_hand="U",
        fallback_split=1.01,
    ) == 1.01


def test_sharpen_does_not_double_count_bullpen_fatigue() -> None:
    """Fatigue/availability stay on the simulator path; sharpen only applies rest stress."""
    tired = MlbGameInputs(
        game_id="g-bp",
        home_team="A",
        away_team="B",
        bullpen_fatigue_home=0.90,
        bullpen_availability_home=0.30,
        bullpen_high_lev_availability_home=0.25,
        bullpen_quality_home=1.0,
        rest_days_home=1.0,
    )
    sharpened, _diag = sharpen_game_inputs(tired, home_abbr="NYY", rest_days_home=1.0)
    assert abs(sharpened.bullpen_quality_home - 1.0) < 1e-9


def test_missing_pitcher_increases_totals_vs_firm_ace() -> None:
    firm = MlbGameInputs(
        game_id="g-firm",
        home_team="A",
        away_team="B",
        starter_home="Ace",
        starter_quality_home=0.90,
        starter_firmness_home=0.95,
        starter_away="Ace2",
        starter_quality_away=0.90,
        starter_firmness_away=0.95,
    )
    missing = MlbGameInputs(
        game_id="g-miss",
        home_team="A",
        away_team="B",
        starter_home=None,
        starter_quality_home=0.90,
        starter_firmness_home=0.40,
        starter_away=None,
        starter_quality_away=0.90,
        starter_firmness_away=0.40,
        uncertainty_total_mul=1.025,
    )
    a = simulate_mlb_game(firm, simulations=1500, seed=7)
    b = simulate_mlb_game(missing, simulations=1500, seed=7)
    assert b["markets"]["fg_total_mean"] >= a["markets"]["fg_total_mean"] - 0.05
