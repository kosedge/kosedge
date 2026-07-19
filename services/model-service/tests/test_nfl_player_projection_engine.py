from __future__ import annotations

from src.services.nfl_player_projection_engine import (
    ROOKIE_EXPERIENCE_CONFIDENCE,
    VETERAN_EXPERIENCE_CONFIDENCE,
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


def _rb_inputs(**overrides) -> PlayerFeatureInputs:
    base = dict(
        position="RB",
        snap_proxy=0.45,
        route_proxy=0.30,
        target_proxy=0.15,
        rush_share=0.55,
        red_zone_share=0.20,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.9,
        role_confidence=0.7,
    )
    base.update(overrides)
    return PlayerFeatureInputs(**base)


def test_rookie_experience_confidence_widens_std_not_mean() -> None:
    veteran = baseline_projection_from_features(_rb_inputs(experience_confidence=VETERAN_EXPERIENCE_CONFIDENCE))
    rookie = baseline_projection_from_features(_rb_inputs(experience_confidence=ROOKIE_EXPERIENCE_CONFIDENCE))

    # Same inputs otherwise -> identical means, wider stds for the rookie.
    assert veteran["rush_yards_mean"] == rookie["rush_yards_mean"]
    assert veteran["receiving_yards_mean"] == rookie["receiving_yards_mean"]
    assert rookie["rush_yards_std"] > veteran["rush_yards_std"]
    assert rookie["receiving_yards_std"] > veteran["receiving_yards_std"]
    assert rookie["uncertainty"]["variance_widening"] > veteran["uncertainty"]["variance_widening"]
    assert veteran["uncertainty"]["variance_widening"] == 1.0


def test_experience_confidence_defaults_to_veteran() -> None:
    default_inputs = _rb_inputs()
    assert default_inputs.experience_confidence == VETERAN_EXPERIENCE_CONFIDENCE
    projection = baseline_projection_from_features(default_inputs)
    assert projection["uncertainty"]["variance_widening"] == 1.0


def test_qb_volume_uses_team_snap_share_not_touch_share() -> None:
    # A starting QB's team_snap_share should be near 1.0 (played nearly
    # every offensive snap) even though their touch-share `snap_proxy` is
    # naturally small (a QB's dropbacks are one slice of the team's total
    # skill-position touches). The old formula blended in snap_proxy at 70%
    # weight, crushing passing volume for every real starter.
    starter = PlayerFeatureInputs(
        position="QB",
        snap_proxy=0.22,  # realistic touch-share value for a real starter
        route_proxy=0.0,
        target_proxy=0.0,
        rush_share=0.05,
        red_zone_share=0.2,
        qb_dropback_factor=0.95,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.5,
        team_snap_share=0.95,
    )
    projection = baseline_projection_from_features(starter)
    # A real starter with a full workload should project well above 200
    # yards for the game -- the pre-fix formula landed around 100.
    assert projection["pass_yards_mean"] > 200


def test_qb_volume_falls_back_to_snap_proxy_when_team_snap_share_missing() -> None:
    # Backward compatibility: a caller that hasn't wired team_snap_share
    # through yet (still at the 0.0 default) shouldn't crash or silently
    # zero out -- it degrades to the old snap_proxy-based signal.
    inputs = PlayerFeatureInputs(
        position="QB",
        snap_proxy=0.8,
        route_proxy=0.0,
        target_proxy=0.0,
        rush_share=0.05,
        red_zone_share=0.2,
        qb_dropback_factor=0.95,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.5,
    )
    projection = baseline_projection_from_features(inputs)
    assert projection["pass_yards_mean"] > 150


def test_opponent_defense_factor_shifts_yards_without_changing_role() -> None:
    base_kwargs = dict(
        position="WR",
        snap_proxy=0.6,
        route_proxy=0.75,
        target_proxy=0.22,
        rush_share=0.0,
        red_zone_share=0.15,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.75,
    )
    vs_bad_defense = baseline_projection_from_features(PlayerFeatureInputs(**base_kwargs, opponent_pass_defense_factor=1.25))
    vs_good_defense = baseline_projection_from_features(PlayerFeatureInputs(**base_kwargs, opponent_pass_defense_factor=0.80))
    assert vs_bad_defense["receiving_yards_mean"] > vs_good_defense["receiving_yards_mean"]
    assert vs_bad_defense["matchup"]["opponent_pass_defense_factor"] == 1.25
    assert vs_good_defense["matchup"]["opponent_pass_defense_factor"] == 0.80


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
