"""Unit tests for KosEdge NFL Decision Engine / Tag Policy."""

from __future__ import annotations

import pytest

from src.services.nfl_decision_engine import (
    BREAKEVEN_ATS_MINUS_110,
    EARLY_SIDE,
    INSEASON_SIDE,
    STANDARD_SIDE,
    assess_confidence,
    assess_market_confirmation,
    build_side_play_to_ladder,
    build_total_play_to_ladder,
    crosses_key_number,
    decide_game,
    decide_side,
    decide_total,
    evaluate_best_bet,
    grade_cover_prob,
    grade_side_points,
    grade_total_points,
    market_past_play_to,
    prefer_key_number_edge,
    side_thresholds_for_week,
    week_regime,
)
from src.services.nfl_tag_policy import (
    BASELINE_TOTAL,
    EARLY_TOTAL,
    WEEK1_TOTAL_BOOST,
    total_thresholds_for_week,
)


def test_doctrine_module_docstring():
    import src.services.nfl_decision_engine as m

    assert "We bet prices, not teams" in (m.__doc__ or "")
    assert "KEI" in (m.__doc__ or "")


def test_breakeven_ats():
    assert abs(BREAKEVEN_ATS_MINUS_110 - 0.5238) < 1e-6


def test_week_regime_default_early():
    assert week_regime(None) == "early"
    assert week_regime(1) == "early"
    assert week_regime(2) == "early"
    assert week_regime(3) == "standard"
    assert week_regime(6) == "inseason"
    assert week_regime(12) == "inseason"
    assert week_regime(13) == "late"


def test_early_thresholds_active_by_default():
    assert side_thresholds_for_week(None) == EARLY_SIDE
    assert side_thresholds_for_week(1) == EARLY_SIDE
    assert side_thresholds_for_week(8) == INSEASON_SIDE
    assert side_thresholds_for_week(4) == STANDARD_SIDE


@pytest.mark.parametrize(
    "edge,week,expected",
    [
        # Week 1–2: 1.25 / 1.75 / 2.25 / 3.25
        (1.24, 1, "PASS"),
        (1.25, 1, "LEAN"),
        (1.75, 1, "LEAN"),
        (2.0, 1, "LEAN"),  # gap to play_min stays LEAN
        (2.24, 1, "LEAN"),
        (2.25, 1, "PLAY"),
        (2.75, 1, "PLAY"),
        (3.0, 1, "PLAY"),  # gap to strong_min stays PLAY
        (3.25, 1, "STRONG PLAY"),
        # Midseason Week 3+: 1.0 / 1.5 / 2.0 / 3.0
        (0.9, 4, "PASS"),
        (1.0, 4, "LEAN"),
        (1.5, 4, "LEAN"),
        (1.9, 4, "LEAN"),
        (2.0, 4, "PLAY"),
        (2.5, 4, "PLAY"),
        (3.0, 4, "STRONG PLAY"),
        (0.9, 8, "PASS"),
        (1.0, 8, "LEAN"),
        (1.5, 8, "LEAN"),
        (2.0, 8, "PLAY"),
        (3.0, 8, "STRONG PLAY"),
    ],
)
def test_side_point_bands(edge, week, expected):
    assert grade_side_points(edge, week) == expected


def test_week1_vs_week6_side_boundary():
    assert grade_side_points(2.0, 1) == "LEAN"
    assert grade_side_points(2.0, 6) == "PLAY"
    assert grade_side_points(2.25, 1) == "PLAY"


@pytest.mark.parametrize(
    "edge,week,expected",
    [
        # Midseason: 1.5 / 2.0 / 2.5 / 3.5
        (1.4, 6, "PASS"),
        (1.5, 6, "LEAN"),
        (2.0, 6, "LEAN"),
        (2.4, 6, "LEAN"),
        (2.5, 6, "PLAY"),
        (3.0, 6, "PLAY"),
        (3.4, 6, "PLAY"),
        (3.5, 6, "STRONG PLAY"),
        # Week 1–2: +0.25 boost → 1.75 / 2.25 / 2.75 / 3.75
        (1.74, 1, "PASS"),
        (1.75, 1, "LEAN"),  # == early pass_max → LEAN
        (2.25, 1, "LEAN"),
        (2.74, 1, "LEAN"),
        (2.75, 1, "PLAY"),
        (3.25, 1, "PLAY"),
        (3.75, 1, "STRONG PLAY"),
    ],
)
def test_total_point_bands(edge, week, expected):
    assert grade_total_points(edge, week) == expected


def test_week1_total_boost_config():
    assert WEEK1_TOTAL_BOOST == 0.25
    assert EARLY_TOTAL.pass_max == 1.75
    assert EARLY_TOTAL.lean_max == 2.25
    assert EARLY_TOTAL.play_min == 2.75
    assert EARLY_TOTAL.strong_min == 3.75
    assert EARLY_SIDE.pass_max == 1.25
    assert EARLY_SIDE.lean_max == 1.75
    assert EARLY_SIDE.play_min == 2.25
    assert EARLY_SIDE.strong_min == 3.25
    assert total_thresholds_for_week(1) == EARLY_TOTAL
    assert total_thresholds_for_week(6) == BASELINE_TOTAL


@pytest.mark.parametrize(
    "p,expected",
    [
        (0.52, "PASS"),
        (0.529, "PASS"),
        (0.53, "LEAN"),
        (0.539, "LEAN"),
        (0.54, "PLAY"),
        (0.55, "PLAY"),
        (0.56, "STRONG PLAY"),
        (0.57, "STRONG PLAY"),
        (0.58, "EXCEPTIONAL"),
        (0.62, "EXCEPTIONAL"),
    ],
)
def test_cover_prob_bands(p, expected):
    assert grade_cover_prob(p) == expected


def test_cover_prob_none():
    assert grade_cover_prob(None) is None


def test_cover_prob_wins_for_tag():
    conf = assess_confidence(base_score=0.8)
    out = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        cover_prob=0.535,
        confidence=conf,
    )
    assert out.point_grade == "STRONG PLAY"
    assert out.cover_grade == "LEAN"
    assert out.action_label == "LEAN"


def test_key_number_cross_spread():
    assert crosses_key_number(-6.0, -3.0, market_kind="spread") is False
    assert crosses_key_number(-6.0, -2.5, market_kind="spread") is True
    assert crosses_key_number(-4.0, -3.5, market_kind="spread") is False


def test_prefer_key_number_equal_edge():
    assert prefer_key_number_edge(2.5, True, 2.5, False) == "a"
    assert prefer_key_number_edge(2.5, False, 2.5, True) == "b"


def test_key_number_elevates_lean_to_play():
    out2 = decide_side(
        fair_spread_home=-5.0,
        market_spread_home=-2.5,
        week=1,
        confidence=assess_confidence(base_score=0.8),
    )
    assert out2.point_grade in ("PLAY", "STRONG PLAY")
    assert out2.key_number_cross is True


def test_side_play_to_ladder_buf_example():
    ladder = build_side_play_to_ladder(
        fair_spread_home=6.0,
        market_spread_home=3.0,
        home_abbr="MIA",
        away_abbr="BUF",
        week=8,
    )
    assert ladder.play_to == -4.0
    assert ladder.lean_to == -4.5
    assert ladder.pass_from == -5.0
    assert "BUF" in ladder.notes


def test_total_play_to_ladder_example():
    ladder = build_total_play_to_ladder(fair_total=47.2, market_total=44.0, week=8)
    assert ladder.play_to == 44.5
    assert ladder.pass_from == 45.5
    assert "Over" in ladder.notes


def test_market_past_play_to_downgrades():
    conf = assess_confidence(base_score=0.8)
    good = decide_side(
        fair_spread_home=-6.0,
        market_spread_home=-3.0,
        week=8,
        confidence=conf,
    )
    assert good.action_label in ("PLAY", "BEST VALUE")
    assert good.play_to is not None
    assert good.play_to.play_to == -4.0

    past = decide_side(
        fair_spread_home=-6.0,
        market_spread_home=-4.5,
        week=8,
        confidence=conf,
    )
    assert past.action_label == "LEAN"
    assert "past_play_to" in past.reason
    assert (
        market_past_play_to(
            market_kind="spread",
            fair=-6.0,
            market=-4.5,
            ladder=good.play_to,
        )
        is True
    )


def test_play_requires_numerical_edge_confidence_and_price():
    conf = assess_confidence(base_score=0.8)
    play = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        confidence=conf,
        price_still_available=True,
    )
    assert play.action_label in ("PLAY", "BEST VALUE")

    no_price = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        confidence=conf,
        price_still_available=False,
    )
    assert no_price.action_label == "ALERT"
    assert "price" in no_price.reason

    low_conf = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(base_score=0.4, qb_clear=False),
        price_still_available=True,
    )
    assert low_conf.action_label in ("ALERT", "STAY AWAY", "LEAN")
    assert low_conf.action_label != "PLAY"


def test_low_confidence_big_edge_is_alert_not_play():
    # |edge| 6.5 inside holdout band — low confidence still blocks PLAY.
    out = decide_side(
        fair_spread_home=-9.5,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(base_score=0.4),
        price_still_available=True,
    )
    assert out.model_confidence.band == "LOW"
    assert out.edge_magnitude >= 3.0
    assert out.action_label == "ALERT"
    assert out.action_label != "PLAY"


def test_best_bet_rejects_raw_discrepancy_alone():
    out = decide_side(
        fair_spread_home=-9.5,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(base_score=0.6, injury_clear=False),
        price_still_available=True,
        matchup_support=True,
    )
    assert out.is_best_bet is False
    assert out.action_label != "BEST VALUE"


def test_best_bet_requires_all_gates():
    conf = assess_confidence(base_score=0.9)
    assert conf.band == "HIGH"
    assert conf.unresolved_flags == ()
    ok = evaluate_best_bet(
        point_grade="STRONG PLAY",
        confidence=conf,
        price_available=True,
        key_number_cross=True,
        market_confirmation=assess_market_confirmation(
            model_fair=-7.0,
            opening=-3.0,
            current=-3.5,
            likes_home_or_over=True,
        ),
        matchup_support=True,
        liquidity_ok=True,
    )
    assert ok is True

    no_matchup = evaluate_best_bet(
        point_grade="STRONG PLAY",
        confidence=conf,
        price_available=True,
        key_number_cross=True,
        market_confirmation=assess_market_confirmation(
            model_fair=-7.0, opening=-3.0, current=-3.5, likes_home_or_over=True
        ),
        matchup_support=False,
        liquidity_ok=True,
    )
    assert no_matchup is False


def test_best_bet_label_when_all_clear():
    out = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(base_score=0.9),
        price_still_available=True,
        matchup_support=True,
        liquidity_ok=True,
    )
    assert out.action_label == "BEST VALUE"
    assert out.is_best_bet is True
    assert out.play_to is not None


def test_edge_and_confidence_kept_separate():
    out = decide_side(
        fair_spread_home=-6.0,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(base_score=0.9),
    )
    assert out.edge_magnitude == pytest.approx(3.0)
    assert out.model_confidence.score >= 0.75
    assert not hasattr(out, "combined_score")


def test_market_confirmation_records_without_mutating_fair():
    mc = assess_market_confirmation(
        model_fair=-6.0,
        opening=-3.0,
        current=-4.0,
        closing=None,
        likes_home_or_over=True,
    )
    assert mc.model_fair == -6.0
    assert mc.opening == -3.0
    assert mc.current == -4.0
    assert "fair unchanged" in mc.note.lower() or "fair line unchanged" in mc.note.lower()


def test_alert_on_uncertainty():
    out = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=1,
        confidence=assess_confidence(base_score=0.7, qb_clear=False),
        price_still_available=True,
    )
    assert out.action_label == "ALERT"


def test_stay_away_on_conflict():
    out = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(conflicting_inputs=True),
        price_still_available=True,
    )
    assert out.action_label == "STAY AWAY"


def test_model_warning_on_60_plus_cover():
    out = decide_side(
        fair_spread_home=-7.0,
        market_spread_home=-3.0,
        week=8,
        cover_prob=0.62,
        confidence=assess_confidence(base_score=0.8),
    )
    assert out.model_warning is True
    assert "model_warning" in out.reason


def test_decide_total_and_game_bundle():
    total = decide_total(
        fair_total=47.2,
        market_total=44.0,
        week=8,
        confidence=assess_confidence(base_score=0.8),
    )
    # Totals PLAY sat (Ryan lock 2026-09-03) — LEAN/PASS/STAY AWAY only.
    assert total.action_label not in ("PLAY", "BEST VALUE")
    assert total.play_to is not None

    game = decide_game(
        week=8,
        fair_spread_home=6.0,
        market_spread_home=3.0,
        fair_total=47.2,
        market_total=44.0,
        home_abbr="MIA",
        away_abbr="BUF",
        confidence=assess_confidence(base_score=0.8),
    )
    assert game["doctrine"] == "We bet prices, not teams."
    assert game["week_regime"] == "inseason"
    assert game["spread"]["play_to"] is not None
    assert game["total"]["play_to"] is not None


def test_spread_play_holdout_band_lock():
    """Ryan lock: 2.19 never PLAY; 2.5 may PLAY; 7.0 never PLAY; totals never PLAY."""
    conf = assess_confidence(base_score=0.72)
    under = decide_side(
        fair_spread_home=-7.81,
        market_spread_home=-10.0,
        week=1,
        cover_prob=0.55,
        confidence=conf,
        price_still_available=True,
    )
    assert under.edge_magnitude == pytest.approx(2.19, abs=0.01)
    assert under.action_label not in ("PLAY", "BEST VALUE")

    at_floor = decide_side(
        fair_spread_home=-6.5,
        market_spread_home=-4.0,
        week=1,
        confidence=conf,
        price_still_available=True,
    )
    assert at_floor.edge_magnitude == pytest.approx(2.5)
    assert at_floor.action_label in ("PLAY", "BEST VALUE")

    at_cap = decide_side(
        fair_spread_home=-10.0,
        market_spread_home=-3.0,
        week=8,
        confidence=conf,
        price_still_available=True,
    )
    assert at_cap.edge_magnitude == pytest.approx(7.0)
    assert at_cap.action_label not in ("PLAY", "BEST VALUE")
    assert "outside_spread_play_v2_cap7" in at_cap.reason

    total = decide_total(
        fair_total=50.0,
        market_total=44.0,
        week=8,
        confidence=assess_confidence(base_score=0.8),
    )
    assert total.action_label not in ("PLAY", "BEST VALUE")


def test_publish_tag_from_action_label_sot():
    from src.services.nfl_side_total_publish_policy import (
        publish_tag_from_action_label,
    )

    assert publish_tag_from_action_label("PLAY") == "PLAY"
    assert publish_tag_from_action_label("BEST VALUE") == "PLAY"
    assert publish_tag_from_action_label("LEAN") == "LEAN"
    assert publish_tag_from_action_label("PASS") == "PASS"
    assert publish_tag_from_action_label("STAY AWAY") == "PASS"
    assert publish_tag_from_action_label("ALERT") == "PASS"


def test_same_game_different_price_different_action():
    conf = assess_confidence(base_score=0.8)
    at_good = decide_side(
        fair_spread_home=-6.0,
        market_spread_home=-3.0,
        week=8,
        confidence=conf,
    )
    at_fair = decide_side(
        fair_spread_home=-6.0,
        market_spread_home=-5.5,
        week=8,
        confidence=conf,
    )
    assert at_good.action_label in ("PLAY", "BEST VALUE", "LEAN")
    assert at_fair.action_label == "PASS"
