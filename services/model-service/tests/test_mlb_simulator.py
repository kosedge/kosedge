from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game
from src.services.mlb_pitch_simulator import simulate_mlb_game_pitch_by_pitch


def test_simulate_mlb_game_outputs_expected_shape() -> None:
    out = simulate_mlb_game(
        MlbGameInputs(
            game_id="game-1",
            home_team="New York Yankees",
            away_team="Boston Red Sox",
            weather_temp_f=74.0,
            weather_wind_mph=8.0,
            weather_humidity_pct=55.0,
            park_factor_runs=1.03,
        ),
        simulations=1500,
        seed=42,
    )
    markets = out["markets"]
    assert out["game_id"] == "game-1"
    assert 0.0 <= markets["f5_home_win_prob"] <= 1.0
    assert 0.0 <= markets["fg_home_win_prob"] <= 1.0
    assert markets["f5_total_mean"] > 0
    assert markets["fg_total_mean"] > 0
    assert isinstance(markets["fair_f5_home_ml"], int)
    assert isinstance(markets["fair_fg_home_ml"], int)
    assert 0.0 <= markets["fg_home_win_prob_ci_low"] <= 1.0
    assert 0.0 <= markets["fg_home_win_prob_ci_high"] <= 1.0
    assert markets["fg_total_p10"] <= markets["fg_total_p50"] <= markets["fg_total_p90"]


def test_simulate_mlb_game_is_stable_with_seed() -> None:
    params = MlbGameInputs(
        game_id="game-2",
        home_team="Atlanta Braves",
        away_team="Philadelphia Phillies",
        weather_temp_f=68.0,
        weather_wind_mph=4.0,
        weather_humidity_pct=45.0,
        park_factor_runs=0.98,
    )
    a = simulate_mlb_game(params, simulations=1000, seed=11)
    b = simulate_mlb_game(params, simulations=1000, seed=11)
    assert a["markets"] == b["markets"]


def test_bullpen_fatigue_moves_full_game_total() -> None:
    baseline = MlbGameInputs(
        game_id="game-3",
        home_team="Texas Rangers",
        away_team="Houston Astros",
        weather_temp_f=72.0,
        weather_wind_mph=7.0,
        weather_humidity_pct=52.0,
        park_factor_runs=1.02,
        bullpen_fatigue_home=0.50,
        bullpen_fatigue_away=0.50,
    )
    stressed = MlbGameInputs(
        game_id="game-3",
        home_team="Texas Rangers",
        away_team="Houston Astros",
        weather_temp_f=72.0,
        weather_wind_mph=7.0,
        weather_humidity_pct=52.0,
        park_factor_runs=1.02,
        bullpen_fatigue_home=0.85,
        bullpen_fatigue_away=0.85,
    )
    a = simulate_mlb_game(baseline, simulations=1200, seed=9)
    b = simulate_mlb_game(stressed, simulations=1200, seed=9)
    assert b["markets"]["fg_total_mean"] > a["markets"]["fg_total_mean"]


def test_low_bullpen_availability_increases_totals() -> None:
    baseline = MlbGameInputs(
        game_id="game-5",
        home_team="Seattle Mariners",
        away_team="Texas Rangers",
        bullpen_availability_home=0.85,
        bullpen_availability_away=0.85,
    )
    stressed = MlbGameInputs(
        game_id="game-5",
        home_team="Seattle Mariners",
        away_team="Texas Rangers",
        bullpen_availability_home=0.35,
        bullpen_availability_away=0.35,
    )
    a = simulate_mlb_game(baseline, simulations=1200, seed=17)
    b = simulate_mlb_game(stressed, simulations=1200, seed=17)
    assert b["markets"]["fg_total_mean"] > a["markets"]["fg_total_mean"]


def test_info_freshness_decays_lineup_driven_edge() -> None:
    fresh = MlbGameInputs(
        game_id="game-6",
        home_team="LA Dodgers",
        away_team="SF Giants",
        offense_home=1.08,
        offense_away=0.94,
        offense_split_home=1.16,
        lineup_strength_index_home=1.14,
        lineup_confidence_home=0.95,
        lineup_confidence_away=0.95,
        info_freshness_score_home=1.0,
        info_freshness_score_away=1.0,
    )
    stale = MlbGameInputs(
        game_id="game-6",
        home_team="LA Dodgers",
        away_team="SF Giants",
        offense_home=1.08,
        offense_away=0.94,
        offense_split_home=1.16,
        lineup_strength_index_home=1.14,
        lineup_confidence_home=0.95,
        lineup_confidence_away=0.95,
        info_freshness_score_home=0.35,
        info_freshness_score_away=0.35,
    )
    a = simulate_mlb_game(fresh, simulations=1800, seed=19)
    b = simulate_mlb_game(stale, simulations=1800, seed=19)
    fresh_edge = abs(a["markets"]["fg_home_win_prob"] - 0.5)
    stale_edge = abs(b["markets"]["fg_home_win_prob"] - 0.5)
    assert stale_edge < fresh_edge


def test_pitch_by_pitch_simulator_is_stable_with_seed() -> None:
    inputs = MlbGameInputs(
        game_id="game-4",
        home_team="Seattle Mariners",
        away_team="Houston Astros",
        weather_temp_f=66.0,
        weather_wind_mph=5.0,
        park_factor_runs=0.96,
        umpire_run_factor=1.02,
    )
    a = simulate_mlb_game_pitch_by_pitch(inputs, simulations=300, seed=21)
    b = simulate_mlb_game_pitch_by_pitch(inputs, simulations=300, seed=21)
    assert a["markets"] == b["markets"]
    assert a["diagnostics"]["simulator_type"] == "pitch_by_pitch"


def test_full_game_moneyline_never_pushes_after_resolution_logic() -> None:
    inputs = MlbGameInputs(
        game_id="game-7",
        home_team="Chicago Cubs",
        away_team="St. Louis Cardinals",
    )
    run_rate = simulate_mlb_game(inputs, simulations=1200, seed=31)
    pitch = simulate_mlb_game_pitch_by_pitch(inputs, simulations=600, seed=31)
    assert run_rate["diagnostics"]["fg_push_rate"] == 0.0
    assert pitch["diagnostics"]["fg_push_rate"] == 0.0
    assert 0.0 <= run_rate["diagnostics"]["extra_innings_rate"] <= 1.0
    assert 0.0 <= pitch["diagnostics"]["extra_innings_rate"] <= 1.0


def test_starter_shape_factors_move_market_outputs() -> None:
    neutral = MlbGameInputs(
        game_id="game-8",
        home_team="Detroit Tigers",
        away_team="Cleveland Guardians",
        starter_quality_home=1.0,
        starter_k_factor_home=1.0,
        starter_bb_factor_home=1.0,
        starter_gb_factor_home=1.0,
    )
    ace_home = MlbGameInputs(
        game_id="game-8",
        home_team="Detroit Tigers",
        away_team="Cleveland Guardians",
        starter_quality_home=0.89,
        starter_k_factor_home=1.16,
        starter_bb_factor_home=0.90,
        starter_gb_factor_home=1.10,
    )
    neutral_run_rate = simulate_mlb_game(neutral, simulations=1600, seed=44)
    ace_run_rate = simulate_mlb_game(ace_home, simulations=1600, seed=44)
    neutral_pitch = simulate_mlb_game_pitch_by_pitch(neutral, simulations=700, seed=44)
    ace_pitch = simulate_mlb_game_pitch_by_pitch(ace_home, simulations=700, seed=44)

    assert ace_run_rate["markets"]["fg_home_win_prob"] > neutral_run_rate["markets"]["fg_home_win_prob"]
    assert ace_run_rate["markets"]["fg_total_mean"] < neutral_run_rate["markets"]["fg_total_mean"]
    assert ace_pitch["markets"]["fg_home_win_prob"] > neutral_pitch["markets"]["fg_home_win_prob"]
    assert ace_pitch["markets"]["fg_total_mean"] < neutral_pitch["markets"]["fg_total_mean"]


def test_offense_context_moves_first_five_more_than_full_game() -> None:
    neutral = MlbGameInputs(
        game_id="game-9",
        home_team="Los Angeles Dodgers",
        away_team="San Diego Padres",
        offense_home=1.02,
        offense_split_home=1.00,
        recent_form_index_home=1.00,
        lineup_strength_index_home=1.00,
    )
    stacked_home = MlbGameInputs(
        game_id="game-9",
        home_team="Los Angeles Dodgers",
        away_team="San Diego Padres",
        offense_home=1.02,
        offense_split_home=1.15,
        recent_form_index_home=1.08,
        lineup_strength_index_home=1.12,
        lineup_confidence_home=0.97,
        info_freshness_score_home=1.0,
    )

    neutral_run_rate = simulate_mlb_game(neutral, simulations=1600, seed=52)
    stacked_run_rate = simulate_mlb_game(stacked_home, simulations=1600, seed=52)
    neutral_pitch = simulate_mlb_game_pitch_by_pitch(neutral, simulations=700, seed=52)
    stacked_pitch = simulate_mlb_game_pitch_by_pitch(stacked_home, simulations=700, seed=52)

    run_rate_f5_delta = (
        stacked_run_rate["markets"]["f5_home_win_prob"] - neutral_run_rate["markets"]["f5_home_win_prob"]
    )
    run_rate_fg_delta = (
        stacked_run_rate["markets"]["fg_home_win_prob"] - neutral_run_rate["markets"]["fg_home_win_prob"]
    )
    pitch_f5_delta = stacked_pitch["markets"]["f5_home_win_prob"] - neutral_pitch["markets"]["f5_home_win_prob"]
    pitch_fg_delta = stacked_pitch["markets"]["fg_home_win_prob"] - neutral_pitch["markets"]["fg_home_win_prob"]

    assert stacked_run_rate["run_rates"]["offense_home_f5"] > stacked_run_rate["run_rates"]["offense_home_full"]
    assert stacked_pitch["run_rates"]["home_offense_early"] > stacked_pitch["run_rates"]["home_offense_late"]
    assert run_rate_f5_delta > run_rate_fg_delta
    assert pitch_f5_delta > 0
    assert pitch_fg_delta > 0


def test_stale_info_shrinks_lineup_strength_signal() -> None:
    fresh = MlbGameInputs(
        game_id="game-10",
        home_team="Seattle Mariners",
        away_team="Houston Astros",
        offense_home=1.01,
        offense_split_home=1.09,
        lineup_strength_index_home=1.18,
        lineup_confidence_home=0.98,
        info_freshness_score_home=1.0,
    )
    stale = MlbGameInputs(
        game_id="game-10",
        home_team="Seattle Mariners",
        away_team="Houston Astros",
        offense_home=1.01,
        offense_split_home=1.09,
        lineup_strength_index_home=1.18,
        lineup_confidence_home=0.98,
        info_freshness_score_home=0.35,
    )

    fresh_run_rate = simulate_mlb_game(fresh, simulations=1600, seed=61)
    stale_run_rate = simulate_mlb_game(stale, simulations=1600, seed=61)
    fresh_pitch = simulate_mlb_game_pitch_by_pitch(fresh, simulations=700, seed=61)
    stale_pitch = simulate_mlb_game_pitch_by_pitch(stale, simulations=700, seed=61)

    assert fresh_run_rate["run_rates"]["offense_home_f5"] > stale_run_rate["run_rates"]["offense_home_f5"]
    assert fresh_pitch["run_rates"]["home_offense_early"] > stale_pitch["run_rates"]["home_offense_early"]
    assert fresh_run_rate["markets"]["fg_home_win_prob"] > stale_run_rate["markets"]["fg_home_win_prob"]
    assert fresh_pitch["markets"]["fg_home_win_prob"] > stale_pitch["markets"]["fg_home_win_prob"]
