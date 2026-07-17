import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_handicapping_framework import (
    compute_nfl_projection_decomposition,
    evaluate_nfl_edge_guardrails,
)


def test_compute_nfl_projection_decomposition_returns_factor_point_space() -> None:
    out = compute_nfl_projection_decomposition(
        offense_index_home=1.08,
        offense_index_away=1.01,
        defense_index_home=0.95,
        defense_index_away=1.03,
        rest_days_home=8.0,
        rest_days_away=6.0,
        matchup_adjustments={"spread_signal": 1.1, "total_signal": 0.8, "components": {"diff_red_zone_td_rate_5g": {"points": 0.6}}},
        totals_adjustments={
            "stdev_points": 0.45,
            "components": {
                "combined_pass_rate_5g": {"points": 0.7},
                "offense_defense_epa_interaction_5g": {"points": 0.6},
                "combined_success_rate_delta_5g": {"points": 0.3},
                "injury_total_signal": {"points": -0.4},
            },
        },
        injury_nowcast_impact_home=0.18,
        injury_nowcast_impact_away=0.25,
        injury_nowcast_freshness_home_hours=20.0,
        injury_nowcast_freshness_away_hours=18.0,
        injury_nowcast_confidence_home=0.74,
        injury_nowcast_confidence_away=0.71,
        injury_nowcast_offense_multiplier_home=0.98,
        injury_nowcast_offense_multiplier_away=0.95,
        injury_nowcast_defense_multiplier_home=1.01,
        injury_nowcast_defense_multiplier_away=1.06,
    )
    assert out["predicted_total"] >= 30.0
    assert "factor_contributions" in out
    assert "base_efficiency" in out["factor_contributions"]
    assert isinstance(out["factor_contributions"]["base_efficiency"]["margin_points"], float)
    assert isinstance(out["factor_contributions"]["rest_travel"]["total_points"], float)
    assert 0.0 <= out["confidence_score"] <= 1.0


def test_compute_nfl_projection_decomposition_marks_missing_data_placeholders() -> None:
    out = compute_nfl_projection_decomposition(
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
    weather = out["factor_contributions"]["weather_environment"]
    injuries = out["factor_contributions"]["injuries_depth"]
    assert weather["available"] is False
    assert injuries["available"] is False
    assert out["factor_coverage"] < 1.0
    assert out["uncertainty_penalties"]["missing_data"] > 0.0


def test_evaluate_nfl_edge_guardrails_returns_reason_codes() -> None:
    guardrails = evaluate_nfl_edge_guardrails(
        edge_prob=0.003,
        quality_score=42.0,
        confidence_score=0.44,
        uncertainty_penalty=0.4,
        factor_coverage=0.4,
        injury_freshness_hours=110.0,
        min_quality_score=58.0,
        min_confidence_score=0.53,
        min_ml_edge_prob=0.01,
    )
    assert guardrails["eligible"] is False
    reason_codes = set(guardrails["reason_codes"])
    assert "quality_score_below_threshold" in reason_codes
    assert "confidence_score_below_threshold" in reason_codes
    assert "edge_prob_below_threshold" in reason_codes
    assert "uncertainty_penalty_exceeded" in reason_codes
    assert "factor_coverage_below_minimum" in reason_codes
    assert "injury_freshness_stale" in reason_codes


def test_compute_nfl_projection_decomposition_weather_travel_bounded() -> None:
    out = compute_nfl_projection_decomposition(
        offense_index_home=1.02,
        offense_index_away=1.01,
        defense_index_home=0.98,
        defense_index_away=1.03,
        rest_days_home=7.0,
        rest_days_away=6.0,
        matchup_adjustments={},
        totals_adjustments={"stdev_points": 0.4},
        injury_nowcast_impact_home=0.1,
        injury_nowcast_impact_away=0.2,
        injury_nowcast_freshness_home_hours=8.0,
        injury_nowcast_freshness_away_hours=9.0,
        injury_nowcast_confidence_home=0.8,
        injury_nowcast_confidence_away=0.75,
        injury_nowcast_offense_multiplier_home=0.99,
        injury_nowcast_offense_multiplier_away=0.97,
        injury_nowcast_defense_multiplier_home=1.02,
        injury_nowcast_defense_multiplier_away=1.03,
        weather_available=True,
        weather_wind_mph=34.0,
        weather_precip_mm=11.5,
        weather_temp_f=18.0,
        travel_available=True,
        travel_miles_home=120.0,
        travel_miles_away=2480.0,
        travel_timezone_delta_home=0.0,
        travel_timezone_delta_away=3.0,
    )
    weather = out["factor_contributions"]["weather_environment"]
    travel = out["factor_contributions"]["travel_schedule"]
    assert weather["available"] is True
    assert travel["available"] is True
    assert abs(float(weather["margin_points"])) <= 0.55
    assert abs(float(weather["total_points"])) <= 2.8
    assert abs(float(travel["margin_points"])) <= 1.75
    assert abs(float(travel["total_points"])) <= 1.6
