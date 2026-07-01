from __future__ import annotations

from src.services.nfl_player_projection_engine import (
    PlayerFeatureInputs,
    baseline_projection_from_features,
    evaluate_prop_edge,
    fantasy_points_from_projection,
)


def test_baseline_projection_is_bounded_and_deterministic() -> None:
    inputs = PlayerFeatureInputs(
        position="WR",
        snap_proxy=0.78,
        route_proxy=0.72,
        target_proxy=0.30,
        rush_share=0.04,
        red_zone_share=0.22,
        qb_dropback_factor=1.04,
        qb_pressure_factor=0.88,
        team_pace_factor=1.05,
        team_pass_rate_factor=1.08,
        availability_confidence=0.91,
        role_confidence=0.85,
    )
    first = baseline_projection_from_features(inputs)
    second = baseline_projection_from_features(inputs)
    assert first == second
    assert first["receiving_yards_mean"] > 0
    assert first["receptions_mean"] > 0
    assert 0.0 <= first["anytime_td_prob"] <= 1.0


def test_prop_edge_behaves_directionally() -> None:
    edge = evaluate_prop_edge(
        model_mean=84.0,
        model_std=14.0,
        line=70.5,
        market_over_price=-110,
        market_under_price=-110,
    )
    assert edge["over_prob"] > edge["under_prob"]
    assert edge["edge_over"] is not None and edge["edge_over"] > 0
    assert isinstance(edge["fair_over_price"], int)


def test_fantasy_scoring_profiles_are_ordered() -> None:
    statline = {
        "pass_yards": 0.0,
        "pass_tds": 0.0,
        "rush_yards": 24.0,
        "rush_tds": 0.3,
        "receiving_yards": 84.0,
        "receptions": 7.0,
        "rec_tds": 0.5,
    }
    standard = fantasy_points_from_projection(scoring_profile="standard", **statline)
    half = fantasy_points_from_projection(scoring_profile="half_ppr", **statline)
    ppr = fantasy_points_from_projection(scoring_profile="ppr", **statline)
    assert standard < half < ppr
