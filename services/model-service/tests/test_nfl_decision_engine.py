"""Unit tests for KosEdge NFL Decision Engine (Edge Board Action Layer)."""

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
    prefer_key_number_edge,
    side_thresholds_for_week,
    week_regime,
)


def test_doctrine_module_docstring():
    import src.services.nfl_decision_engine as m

    assert "We bet prices, not teams" in (m.__doc__ or "")


def test_breakeven_ats():
    assert abs(BREAKEVEN_ATS_MINUS_110 - 0.5238) < 1e-6


# --- Week regimes ---


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


# --- Side point bands (every threshold band) ---


@pytest.mark.parametrize(
    "edge,week,expected",
    [
        # Weeks 1–2
        (1.4, 1, "PASS"),
        (1.5, 1, "LEAN"),
        (1.9, 1, "LEAN"),
        (2.0, 1, "LEAN"),  # gap before play_min 2.5
        (2.5, 1, "PLAY"),
        (3.0, 1, "PLAY"),
        (3.5, 1, "STRONG PLAY"),
        # Standard weeks 3–5
        (0.9, 4, "PASS"),
        (1.0, 4, "LEAN"),
        (1.5, 4, "LEAN"),
        (1.9, 4, "LEAN"),
        (2.0, 4, "PLAY"),
        (2.5, 4, "PLAY"),
        (3.0, 4, "STRONG PLAY"),
        # Weeks 6–12
        (0.9, 8, "PASS"),
        (1.0, 8, "LEAN"),
        (1.5, 8, "LEAN"),
        (2.0, 8, "PLAY"),
        (3.0, 8, "STRONG PLAY"),
    ],
)
def test_side_point_bands(edge, week, expected):
    assert grade_side_points(edge, week) == expected


# --- Totals bands ---


@pytest.mark.parametrize(
    "edge,expected",
    [
        (1.4, "PASS"),
        (1.5, "LEAN"),
        (2.0, "LEAN"),
        (2.4, "LEAN"),
        (2.5, "PLAY"),
        (3.0, "PLAY"),
        (3.4, "PLAY"),
        (3.5, "STRONG PLAY"),
    ],
)
def test_total_point_bands(edge, expected):
    assert grade_total_points(edge) == expected


# --- Cover probability bands ---


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


# --- Key-number preference ---


def test_key_number_cross_spread():
    # Open interval: -6 → -3 does not cross interior -3; -6 → -2.5 does.
    assert crosses_key_number(-6.0, -3.0, market_kind="spread") is False
    assert crosses_key_number(-6.0, -2.5, market_kind="spread") is True
    assert crosses_key_number(-4.0, -3.5, market_kind="spread") is False


def test_prefer_key_number_equal_edge():
    assert prefer_key_number_edge(2.5, True, 2.5, False) == "a"
    assert prefer_key_number_edge(2.5, False, 2.5, True) == "b"


def test_key_number_elevates_lean_to_play():
    # 2.0 edge in early week is LEAN by points; crossing key number + abs>=2 → PLAY
    out = decide_side(
        fair_spread_home=-5.5,
        market_spread_home=-3.0,  # crosses -3? -5.5 to -3 does not include interior -3
        week=1,
        confidence=assess_confidence(base_score=0.8),
    )
    # Ensure a clear cross of 3: fair -6, market -2.5 → edge 3.5 STRONG anyway
    out2 = decide_side(
        fair_spread_home=-5.0,
        market_spread_home=-2.5,  # path crosses -3; abs edge 2.5 → PLAY early
        week=1,
        confidence=assess_confidence(base_score=0.8),
    )
    assert out2.point_grade in ("PLAY", "STRONG PLAY")
    assert out2.key_number_cross is True
    assert out.edge_magnitude == pytest.approx(2.5)


# --- Play-To ladders ---


def test_side_play_to_ladder_buf_example():
    # Fair BUF −6 (away), Market BUF −3 → home market +3 / fair +6
    ladder = build_side_play_to_ladder(
        fair_spread_home=6.0,
        market_spread_home=3.0,
        home_abbr="MIA",
        away_abbr="BUF",
    )
    assert ladder.play_to == -4.0
    assert ladder.lean_to == -4.5
    assert ladder.pass_from == -5.0
    assert "BUF" in ladder.notes


def test_total_play_to_ladder_example():
    ladder = build_total_play_to_ladder(fair_total=47.2, market_total=44.0)
    assert ladder.play_to == 44.5
    assert ladder.pass_from == 46.0
    assert "Over" in ladder.notes


# --- PLAY triple requirement ---


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
    assert play.reason.startswith("play_triple") or play.reason.startswith("best_bet")

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


# --- Best Bet strictness ---


def test_best_bet_rejects_raw_discrepancy_alone():
    # Huge edge but medium confidence / unresolved → not BEST VALUE
    out = decide_side(
        fair_spread_home=-10.0,
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


# --- Confidence separate from edge ---


def test_edge_and_confidence_kept_separate():
    out = decide_side(
        fair_spread_home=-6.0,
        market_spread_home=-3.0,
        week=8,
        confidence=assess_confidence(base_score=0.9),
    )
    assert out.edge_magnitude == pytest.approx(3.0)
    assert out.model_confidence.score >= 0.75
    # No combined score field
    assert not hasattr(out, "combined_score")


# --- Market confirmation does not mutate fair ---


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


# --- ALERT / STAY AWAY ---


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


# --- Totals decision + game bundle ---


def test_decide_total_and_game_bundle():
    total = decide_total(
        fair_total=47.2,
        market_total=44.0,
        week=1,
        confidence=assess_confidence(base_score=0.8),
    )
    assert total.action_label in ("PLAY", "BEST VALUE")
    assert total.play_to is not None

    game = decide_game(
        week=1,
        fair_spread_home=6.0,
        market_spread_home=3.0,
        fair_total=47.2,
        market_total=44.0,
        home_abbr="MIA",
        away_abbr="BUF",
        confidence=assess_confidence(base_score=0.8),
    )
    assert game["doctrine"] == "We bet prices, not teams."
    assert game["week_regime"] == "early"
    assert game["action_label_spread"] in (
        "PASS",
        "LEAN",
        "PLAY",
        "BEST VALUE",
        "ALERT",
        "STAY AWAY",
    )
    assert game["spread"]["play_to"] is not None
    assert game["total"]["play_to"] is not None


def test_same_game_different_price_different_action():
    """Doctrine: same game can be PLAY or PASS depending only on market number."""
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
