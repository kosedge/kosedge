import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_simulator import (
    DEFAULT_NFL_MODEL_VERSION,
    NFL_MARKET_BLEND_SPREAD_WEIGHT,
    NFL_MARKET_BLEND_TOTAL_WEIGHT,
    NflGameInputs,
    simulate_nfl_game,
)


def test_higher_defense_index_favors_that_teams_own_win_probability() -> None:
    """`defense_index` is "higher = stronger defense" (see
    tasks.py::_load_team_strength_priors, which derives it from *negative*
    EPA allowed, and compute_nfl_projection_decomposition, which divides
    the opponent's offense_index by it). This directly exercises that
    contract so a future change can't silently invert it again -- an
    inversion previously slipped in via how the in-season injury nowcast's
    defense_multiplier (documented "higher = weaker defense") was combined
    with defense_index in tasks.py/routes.py: multiplying a >1.0 "weaker
    defense" multiplier directly into defense_index made an injured team's
    defense look *stronger* in this formula. The fix (see
    run_nfl_market_simulations) divides instead of multiplies -- this test
    guards against regressing that."""
    base_inputs = dict(
        game_id="g-defense-sign",
        home_team="CLE",
        away_team="BAL",
        offense_index_home=1.0,
        offense_index_away=1.0,
        defense_index_away=1.0,
        rest_days_home=7.0,
        rest_days_away=7.0,
    )
    baseline = simulate_nfl_game(NflGameInputs(defense_index_home=1.0, **base_inputs), simulations=15000, seed=7)
    weaker_defense = simulate_nfl_game(NflGameInputs(defense_index_home=0.90, **base_inputs), simulations=15000, seed=7)
    stronger_defense = simulate_nfl_game(NflGameInputs(defense_index_home=1.10, **base_inputs), simulations=15000, seed=7)

    assert weaker_defense["markets"]["home_win_prob"] < baseline["markets"]["home_win_prob"]
    assert stronger_defense["markets"]["home_win_prob"] > baseline["markets"]["home_win_prob"]


def test_injury_nowcast_defense_multiplier_should_be_applied_as_divisor() -> None:
    """Mirrors exactly how tasks.py::run_nfl_market_simulations combines a
    team-strength-prior defense_index with the injury/roster-continuity
    nowcast's defense_multiplier: `defense_index_home = prior / multiplier`.
    A multiplier > 1.0 ("weaker defense") must reduce the resulting
    defense_index and therefore reduce that team's own win probability."""
    prior_defense_index = 1.0
    weaker_multiplier = 1.0446  # e.g. a lost star defender

    def _combined_inputs(defense_multiplier: float) -> NflGameInputs:
        return NflGameInputs(
            game_id="g-divisor",
            home_team="CLE",
            away_team="BAL",
            offense_index_home=1.0,
            offense_index_away=1.0,
            defense_index_home=prior_defense_index / defense_multiplier,
            defense_index_away=1.0,
            injury_nowcast_defense_multiplier_home=defense_multiplier,
            injury_nowcast_defense_multiplier_away=1.0,
            injury_nowcast_offense_multiplier_home=1.0,
            injury_nowcast_offense_multiplier_away=1.0,
            injury_nowcast_confidence_home=0.8,
            injury_nowcast_confidence_away=0.0,
            injury_nowcast_impact_home=0.028,
            injury_nowcast_impact_away=0.0,
            rest_days_home=7.0,
            rest_days_away=7.0,
        )

    healthy = simulate_nfl_game(_combined_inputs(1.0), simulations=15000, seed=42)
    weakened = simulate_nfl_game(_combined_inputs(weaker_multiplier), simulations=15000, seed=42)
    assert weakened["markets"]["home_win_prob"] < healthy["markets"]["home_win_prob"]


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
    framework = out["diagnostics"]["framework"]
    assert framework["framework_version"] == "nfl-handicap-core-v1"
    assert framework["factor_contributions"]["weather_environment"]["available"] is False
    assert out["diagnostics"]["mean_home_points"] == round(float(out["decomposition"]["expected_home_points"]), 3)
    assert out["diagnostics"]["mean_away_points"] == round(float(out["decomposition"]["expected_away_points"]), 3)


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
    assert out["decomposition"]["factor_contributions"]["weather_environment"]["available"] is False


def test_market_blend_defaults_are_empirically_tuned() -> None:
    # See scripts/nfl/historical_market_backtest.py and
    # data/ops/nfl-market-blend-backtest-*.json: 0.30 minimized MAE vs actual
    # outcomes across 3,562 games (2013-2025) using free nflverse closing lines.
    assert NFL_MARKET_BLEND_SPREAD_WEIGHT == 0.30
    assert NFL_MARKET_BLEND_TOTAL_WEIGHT == 0.30


def test_market_blend_shifts_spread_toward_market_line() -> None:
    inputs = NflGameInputs(
        game_id="g-market-spread",
        home_team="Cleveland Browns",
        away_team="Jacksonville Jaguars",
        offense_index_home=0.87,
        offense_index_away=1.0,
        defense_index_home=1.07,
        defense_index_away=1.0,
    )
    baseline = simulate_nfl_game(inputs, simulations=2000, seed=42)
    baseline_spread = baseline["markets"]["spread_home"]

    # Market has the home team (CLE) as a much bigger underdog than the raw
    # model does -- spread_home here uses the "negative = home favored"
    # (The Odds API) convention, matching what run_nfl_market_simulations
    # fetches from odds_snapshots live.
    market_spread_home = baseline_spread - 6.0
    blended = simulate_nfl_game(
        inputs,
        simulations=2000,
        seed=42,
        market_spread_home=market_spread_home,
    )
    blended_spread = blended["markets"]["spread_home"]

    # Blended spread should land strictly between the raw model's number and
    # the market's number, moved by roughly the configured weight.
    assert min(baseline_spread, market_spread_home) < blended_spread < max(baseline_spread, market_spread_home)
    expected = baseline_spread + (NFL_MARKET_BLEND_SPREAD_WEIGHT * (market_spread_home - baseline_spread))
    assert abs(blended_spread - expected) < 0.75  # small tolerance for Monte Carlo noise

    diag = blended["diagnostics"]["market_blend"]
    assert diag["spread_applied"] is True
    assert diag["market_spread_home"] == round(market_spread_home, 3)


def test_market_blend_shifts_total_toward_market_line() -> None:
    inputs = NflGameInputs(game_id="g-market-total", home_team="SEA", away_team="ARI")
    baseline = simulate_nfl_game(inputs, simulations=2000, seed=11)
    baseline_total = baseline["markets"]["total_mean"]
    market_total = baseline_total + 8.0

    blended = simulate_nfl_game(
        inputs,
        simulations=2000,
        seed=11,
        market_total=market_total,
    )
    blended_total = blended["markets"]["total_mean"]

    assert baseline_total < blended_total < market_total
    diag = blended["diagnostics"]["market_blend"]
    assert diag["total_applied"] is True
    assert diag["market_total"] == round(market_total, 3)


def test_market_blend_not_applied_when_no_market_line() -> None:
    inputs = NflGameInputs(game_id="g-no-market", home_team="DAL", away_team="NYG")
    out = simulate_nfl_game(inputs, simulations=400, seed=3)
    diag = out["diagnostics"]["market_blend"]
    assert diag == {"spread_applied": False, "total_applied": False}


def test_early_season_side_disagreement_boosts_market_blend() -> None:
    """When week-1 raw margin favors home but market has home as a dog,
    blend weight must rise above the ordinary early-season boost."""
    from src.services.nfl_simulator import (
        _early_season_side_disagreement_boost,
        _market_blend_weight_for_week,
    )

    # Home favored raw (+4 margin) vs market home dog (+2.6 spread => -2.6 margin)
    boost = _early_season_side_disagreement_boost(
        season_week=1,
        pre_blend_margin=4.0,
        market_spread_home=2.6,
    )
    assert boost == 0.30
    base = _market_blend_weight_for_week(0.30, 1)
    assert base == 0.55
    assert _clamp_blend(base + boost) >= 0.85

    # Same side as market → no disagreement boost
    assert (
        _early_season_side_disagreement_boost(
            season_week=1,
            pre_blend_margin=-3.0,
            market_spread_home=2.6,
        )
        == 0.0
    )
    # Week 5+ → no boost
    assert (
        _early_season_side_disagreement_boost(
            season_week=5,
            pre_blend_margin=4.0,
            market_spread_home=2.6,
        )
        == 0.0
    )


def _clamp_blend(weight: float) -> float:
    return max(0.0, min(0.85, weight))


def test_week1_pack_aligned_indices_stay_dog_side_of_market() -> None:
    """Integration guard for the DAL@NYG class of failure: week-1 pack EPA
    that favors the away club + market home dog must not publish a home
    favorite near -3 after early-season market blend."""
    from src.services.nfl_matchup_features import matchup_pack_to_sim_input_kwargs
    from src.tasks import _priors_from_matchup_pack

    pack = {
        "season": 2026,
        "week": 1,
        "game_id": "2026_01_AWAY_HOME",
        "home_team": "HOME",
        "away_team": "AWAY",
        "home_off_epa_5g": -0.05165,
        "away_off_epa_5g": 0.03415,
        "home_def_epa_allowed_5g": 0.07218,
        "away_def_epa_allowed_5g": 0.07718,
        "home_pressure_generated_5g": 0.1694,
        "away_pressure_generated_5g": 0.1775,
        "home_pressure_allowed_5g": 0.2068,
        "away_pressure_allowed_5g": 0.1393,
        "home_pass_rate_5g": 0.53,
        "away_pass_rate_5g": 0.59,
        "home_red_zone_td_rate_5g": 0.16,
        "away_red_zone_td_rate_5g": 0.20,
        "home_success_offense_5g": 0.42,
        "away_success_offense_5g": 0.46,
        "home_success_defense_allowed_5g": 0.47,
        "away_success_defense_allowed_5g": 0.49,
        "diff_off_epa_5g": -0.0858,
        "diff_def_epa_allowed_5g": 0.0050,
        "diff_pressure_generated_5g": -0.0081,
        "diff_pressure_allowed_5g": -0.0675,
        "diff_red_zone_td_rate_5g": -0.0391,
    }
    home_prior, away_prior = _priors_from_matchup_pack(pack)
    mk = matchup_pack_to_sim_input_kwargs(pack)
    inputs = NflGameInputs(
        game_id="g-early-pack",
        home_team="Home",
        away_team="Away",
        offense_index_home=float(home_prior["offense_index"]),
        offense_index_away=float(away_prior["offense_index"]),
        defense_index_home=float(home_prior["defense_index"]),
        defense_index_away=float(away_prior["defense_index"]),
        **mk,
    )
    out = simulate_nfl_game(
        inputs,
        simulations=3000,
        seed=7,
        market_spread_home=2.6,
        market_total=48.2,
        apply_linear_totals_calibration=False,
    )
    spread = float(out["markets"]["spread_home"])
    # Must stay on the market dog side (positive home spread) or within ~1.5
    # of market — never a heavy home favorite like -3.
    assert spread > -1.5
    assert spread > 0.0 or abs(spread - 2.6) <= 1.5


def test_simulator_environment_contributions_activate_when_available() -> None:
    inputs = NflGameInputs(
        game_id="g-env",
        home_team="Seattle Seahawks",
        away_team="Miami Dolphins",
        weather_available=True,
        weather_wind_mph=24.0,
        weather_precip_mm=3.2,
        weather_temp_f=33.0,
        travel_available=True,
        travel_miles_home=0.0,
        travel_miles_away=2725.0,
        travel_timezone_delta_home=0.0,
        travel_timezone_delta_away=3.0,
    )
    out = simulate_nfl_game(inputs, simulations=700, seed=31)
    factors = out["decomposition"]["factor_contributions"]
    assert factors["weather_environment"]["available"] is True
    assert factors["travel_schedule"]["available"] is True
    assert abs(float(factors["weather_environment"]["total_points"])) <= 2.8
    assert abs(float(factors["travel_schedule"]["margin_points"])) <= 1.75
