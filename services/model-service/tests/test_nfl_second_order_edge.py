"""Pure-function tests for narrow second-order edge factors and helpers."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from data_platform_nfl.coach_aggression import (
    compute_aggression_latent,
    compute_pace_latent,
    expected_fourth_down_go_rate,
)
from data_platform_nfl.external_sources import external_source_status
from data_platform_nfl.personnel_efficiency import (
    bucket_personnel,
    compute_personnel_edge,
    compute_substitution_elasticity,
    parse_offense_personnel,
)
from src.services.nfl_injury_nowcast import (
    compute_player_status_delta,
    compute_team_info_velocity,
)
from src.services.nfl_second_order_factors import (
    compute_error_regime_uncertainty,
    compute_travel_weather_interaction,
    usage_elasticity_tilt,
)
from src.services.nfl_handicapping_framework import compute_nfl_projection_decomposition


def _base_kwargs(**overrides):
    base = dict(
        offense_index_home=1.0,
        offense_index_away=1.0,
        defense_index_home=1.0,
        defense_index_away=1.0,
        rest_days_home=7.0,
        rest_days_away=7.0,
        matchup_adjustments={},
        totals_adjustments={},
        injury_nowcast_impact_home=None,
        injury_nowcast_impact_away=None,
        injury_nowcast_freshness_home_hours=None,
        injury_nowcast_freshness_away_hours=None,
        injury_nowcast_confidence_home=None,
        injury_nowcast_confidence_away=None,
        injury_nowcast_offense_multiplier_home=None,
        injury_nowcast_offense_multiplier_away=None,
        injury_nowcast_defense_multiplier_home=None,
        injury_nowcast_defense_multiplier_away=None,
    )
    base.update(overrides)
    return base


def test_parse_offense_personnel_codes() -> None:
    assert parse_offense_personnel("1 RB, 1 TE, 3 WR") == "11"
    assert parse_offense_personnel("1 RB, 2 TE, 2 WR") == "12"
    assert parse_offense_personnel("2 RB, 1 TE, 2 WR") == "21"
    assert parse_offense_personnel("11") == "11"
    assert parse_offense_personnel(None) is None
    assert bucket_personnel("10") == "11"
    assert bucket_personnel("99") == "other"


def test_compute_personnel_edge_bounded() -> None:
    edge = compute_personnel_edge(
        rates={"11": 0.7, "12": 0.3},
        epas={"11": 0.10, "12": -0.02},
        league_epa={"11": 0.0, "12": 0.0},
    )
    assert -3.0 <= edge <= 3.0
    assert edge > 0


def test_substitution_elasticity_needs_sample() -> None:
    mean, vol, elast = compute_substitution_elasticity(
        snap_pcts=[0.4, 0.5, 0.6],
        epa_values=[0.01, 0.02, 0.03],
    )
    assert mean is None
    mean, vol, elast = compute_substitution_elasticity(
        snap_pcts=[0.3, 0.4, 0.5, 0.6, 0.7],
        epa_values=[0.0, 0.01, 0.02, 0.03, 0.04],
    )
    assert mean is not None
    assert elast is not None
    assert -2.0 <= elast <= 2.0


def test_usage_elasticity_tilt_bounded() -> None:
    assert usage_elasticity_tilt(base_usage=0.55, elasticity_5g=None) == 0.55
    tilted = usage_elasticity_tilt(base_usage=0.55, elasticity_5g=1.5)
    assert 0.55 < tilted <= 0.55 * 1.04 + 1e-9


def test_coach_aggression_helpers_thin() -> None:
    go = expected_fourth_down_go_rate(
        ydstogo=1.0,
        yardline_100=40.0,
        score_differential=-7.0,
        game_seconds_remaining=300.0,
    )
    assert 0.05 <= go <= 0.92
    # Thin formula: 4th residual + tempo only (PROE/pass-state ignored).
    agg_a = compute_aggression_latent(
        fourth_go_residual=0.15,
        early_down_proe=0.50,
        no_huddle_rate=0.12,
        trailing_pass_rate=0.90,
        leading_pass_rate=0.10,
    )
    agg_b = compute_aggression_latent(
        fourth_go_residual=0.15,
        early_down_proe=-0.50,
        no_huddle_rate=0.12,
        trailing_pass_rate=0.10,
        leading_pass_rate=0.90,
    )
    assert agg_a == agg_b
    assert -2.0 <= agg_a <= 2.0
    pace = compute_pace_latent(no_huddle_rate=0.20, plays_per_game_proxy=70.0)
    assert pace > 0


def test_info_velocity_upgrade_downgrade() -> None:
    downgrade = compute_player_status_delta(
        prior_report="questionable",
        prior_practice="limited",
        current_report="out",
        current_practice="did not participate",
        position="QB",
    )
    assert downgrade["direction"] == "downgrade"
    assert downgrade["weighted_delta"] > 0

    upgrade = compute_player_status_delta(
        prior_report="out",
        prior_practice="did not participate",
        current_report="questionable",
        current_practice="limited",
        position="WR",
    )
    assert upgrade["direction"] == "upgrade"
    assert upgrade["weighted_delta"] < 0

    prior = [
        {
            "player_key": "qb1",
            "player_name": "QB One",
            "position": "QB",
            "report_status": "questionable",
            "practice_status": "limited",
        }
    ]
    current = [
        {
            "player_key": "qb1",
            "player_name": "QB One",
            "position": "QB",
            "report_status": "out",
            "practice_status": "did not participate",
            "updated_at": None,
        }
    ]
    vel = compute_team_info_velocity(current, prior)
    assert vel["downgrade_count"] >= 1
    assert vel["velocity_score"] > 0


def test_travel_weather_interaction_skips_and_bounds() -> None:
    skipped = compute_travel_weather_interaction(
        travel_miles_away=2000,
        travel_miles_home=0,
        travel_timezone_delta_away=3,
        travel_timezone_delta_home=0,
        weather_wind_mph=20,
        weather_precip_mm=5,
        weather_temp_f=30,
        weather_available=False,
        travel_available=True,
    )
    assert skipped["available"] is False
    assert skipped["margin_points"] == 0.0

    active = compute_travel_weather_interaction(
        travel_miles_away=2500,
        travel_miles_home=0,
        travel_timezone_delta_away=3,
        travel_timezone_delta_home=0,
        weather_wind_mph=22,
        weather_precip_mm=8,
        weather_temp_f=25,
        weather_available=True,
        travel_available=True,
    )
    assert active["available"] is True
    assert abs(active["margin_points"]) <= 0.75
    assert abs(active["total_points"]) <= 1.4
    assert active["margin_points"] >= 0  # home-friendly under away travel + bad weather


def test_error_regime_widens_without_point_shift() -> None:
    regime = compute_error_regime_uncertainty(
        info_velocity_abs=1.2,
        hours_since_injury_change=3.0,
        weather_available=False,
        factor_coverage=0.6,
        injury_impact=0.4,
    )
    assert regime["margin_points"] == 0.0
    assert regime["total_points"] == 0.0
    assert regime["stdev_widen"] > 0
    assert regime["confidence_penalty"] > 0
    assert regime["stdev_widen"] <= 0.85


def test_personnel_coach_info_velocity_in_decomposition() -> None:
    # Opt-in killed factors for pure-fn wiring checks (defaults are OFF post-ablation).
    enable_all = {
        "factors": {
            "personnel_efficiency": {"enabled": True},
            "coach_aggression": {"enabled": True},
            "info_velocity": {"enabled": True},
            "travel_weather_interaction": {"enabled": True},
            "error_regime": {"enabled": True},
        }
    }
    base = compute_nfl_projection_decomposition(**_base_kwargs(config_overrides=enable_all))
    with_factors = compute_nfl_projection_decomposition(
        **_base_kwargs(
            home_personnel_edge_5g=1.2,
            away_personnel_edge_5g=-0.4,
            home_sub_elasticity_5g=0.2,
            away_sub_elasticity_5g=-0.1,
            home_coach_aggression_5g=0.9,
            away_coach_aggression_5g=-0.3,
            home_coach_pace_5g=0.4,
            away_coach_pace_5g=0.2,
            second_order_as_of_week=8,
            info_velocity_home=0.8,
            info_velocity_away=-0.2,
            hours_since_change_home=4.0,
            hours_since_change_away=20.0,
            weather_available=True,
            weather_wind_mph=18.0,
            weather_precip_mm=4.0,
            weather_temp_f=35.0,
            travel_available=True,
            travel_miles_home=0.0,
            travel_miles_away=2200.0,
            travel_timezone_delta_home=0.0,
            travel_timezone_delta_away=3.0,
            config_overrides=enable_all,
        )
    )
    pers = with_factors["factor_contributions"]["personnel_efficiency"]
    coach = with_factors["factor_contributions"]["coach_aggression"]
    info = with_factors["factor_contributions"]["info_velocity"]
    tw = with_factors["factor_contributions"]["travel_weather_interaction"]
    err = with_factors["factor_contributions"]["error_regime"]
    assert pers["available"] is True
    assert coach["available"] is True
    assert info["available"] is True
    assert tw["available"] is True
    assert err["available"] is True
    assert pers["margin_points"] > 0
    assert coach["margin_points"] > 0
    # Home downgrades (higher velocity) → negative margin for home.
    assert info["margin_points"] < 0
    assert err["margin_points"] == 0.0
    assert with_factors["error_regime_stdev_widen"] >= 0.0
    assert abs(pers["margin_points"]) <= 1.6
    assert abs(coach["margin_points"]) <= 1.1
    assert abs(info["margin_points"]) <= 1.2
    assert with_factors["predicted_margin"] != base["predicted_margin"]


def test_disabled_second_order_factors_do_not_penalize_coverage() -> None:
    out = compute_nfl_projection_decomposition(
        **_base_kwargs(
            config_overrides={
                "factors": {
                    "personnel_efficiency": {"enabled": False},
                    "coach_aggression": {"enabled": False},
                    "info_velocity": {"enabled": False},
                    "travel_weather_interaction": {"enabled": False},
                    "error_regime": {"enabled": False},
                }
            }
        )
    )
    for key in (
        "personnel_efficiency",
        "coach_aggression",
        "info_velocity",
        "travel_weather_interaction",
        "error_regime",
    ):
        assert out["factor_contributions"][key]["available"] is True
        assert out["factor_contributions"][key]["margin_points"] == 0.0


def test_external_source_status_vc_only() -> None:
    status = external_source_status()
    assert "visual_crossing" in status
    assert "deferred" in status
    assert "otc" not in status or "otc" in status.get("deferred", {})
    assert status["deferred"]["pff"] == "not_implemented_holdout_deferred"
