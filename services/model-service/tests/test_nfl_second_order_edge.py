"""Pure-function tests for second-order edge factors and helpers."""

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


def test_coach_aggression_helpers() -> None:
    go = expected_fourth_down_go_rate(
        ydstogo=1.0,
        yardline_100=40.0,
        score_differential=-7.0,
        game_seconds_remaining=300.0,
    )
    assert 0.05 <= go <= 0.92
    agg = compute_aggression_latent(
        fourth_go_residual=0.15,
        early_down_proe=0.08,
        no_huddle_rate=0.12,
        trailing_pass_rate=0.65,
        leading_pass_rate=0.45,
    )
    assert -2.0 <= agg <= 2.0
    assert agg > 0
    pace = compute_pace_latent(no_huddle_rate=0.20, plays_per_game_proxy=70.0)
    assert pace > 0


def test_personnel_and_coach_factors_move_margin() -> None:
    base = compute_nfl_projection_decomposition(**_base_kwargs())
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
        )
    )
    pers = with_factors["factor_contributions"]["personnel_efficiency"]
    coach = with_factors["factor_contributions"]["coach_aggression"]
    assert pers["available"] is True
    assert coach["available"] is True
    assert pers["margin_points"] > 0
    assert coach["margin_points"] > 0
    assert abs(pers["margin_points"]) <= 1.6
    assert abs(coach["margin_points"]) <= 1.4
    assert with_factors["predicted_margin"] > base["predicted_margin"]
    assert "home_personnel_edge_5g" in pers["raw_signals"]
    assert "home_coach_aggression_5g" in coach["raw_signals"]


def test_disabled_second_order_factors_do_not_penalize_coverage() -> None:
    out = compute_nfl_projection_decomposition(
        **_base_kwargs(
            config_overrides={
                "factors": {
                    "personnel_efficiency": {"enabled": False},
                    "coach_aggression": {"enabled": False},
                }
            }
        )
    )
    assert out["factor_contributions"]["personnel_efficiency"]["available"] is True
    assert out["factor_contributions"]["coach_aggression"]["available"] is True
    assert out["factor_contributions"]["personnel_efficiency"]["margin_points"] == 0.0
    assert out["factor_contributions"]["coach_aggression"]["margin_points"] == 0.0


def test_external_source_status_is_safe_without_keys() -> None:
    status = external_source_status()
    assert "visual_crossing" in status
    assert "otc" in status
    assert "spotrac" in status
    assert "pff" in status
    assert status["otc"]["enabled"] is False or isinstance(status["otc"]["enabled"], bool)
