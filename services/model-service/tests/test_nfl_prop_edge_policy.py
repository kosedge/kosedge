from src.services.nfl_prop_edge_policy import (
    PROP_COVERAGE_MAX,
    PROP_RELIABILITY_BASE,
    anytime_td_prob_from_td_mean,
    assess_prop_reliability,
    classify_prop_tag,
    devig_two_way,
    evaluate_prop_edge,
)


def test_devig_two_way_removes_juice() -> None:
    fair_over, fair_under, vig = devig_two_way(-110, -110)
    assert fair_over is not None and fair_under is not None
    assert abs(fair_over + fair_under - 1.0) < 1e-6
    assert vig is not None and vig > 0.04


def test_rec_play_requires_z_060_but_not_stake_eligible() -> None:
    # z = (82-64.5)/18 ≈ 0.97 → research highlight; stake blocked post batch-5
    # Surface integrity: no PLAY tag when stake_eligible is false → WATCH.
    edge = evaluate_prop_edge(
        model_mean=82.0,
        model_std=18.0,
        line=64.5,
        market_over_price=-110,
        market_under_price=-110,
        market_key="rec_yds",
        position="WR",
        role_confidence=0.8,
        availability_confidence=0.9,
    )
    assert edge["tag"] == "WATCH"
    assert edge["stake_eligible"] is False
    assert edge["tag_reason"] == "rec_yds_research_unconfirmed"


def test_rec_mid_z_is_watch_not_play() -> None:
    # z = (70-64.5)/18 ≈ 0.306 → below WATCH? need ~0.35 for watch
    # use z≈0.55 → WATCH (below PLAY 0.60)
    tag = classify_prop_tag(
        market_key="rec_yds",
        position="WR",
        z_over=0.55,
        edge_over=0.06,
        edge_under=-0.06,
        market_joined=True,
        model_mean=74.0,
        line=64.5,
        role_confidence=0.8,
        availability_confidence=0.9,
    )
    assert tag["tag"] == "WATCH"
    assert tag["stake_eligible"] is False


def test_rush_is_watch_only_after_holdout() -> None:
    tag = classify_prop_tag(
        market_key="rush_yds",
        position="RB",
        z_over=0.75,
        edge_over=0.07,
        edge_under=-0.07,
        market_joined=True,
        model_mean=72.0,
        line=58.5,
        role_confidence=0.9,
        availability_confidence=0.9,
    )
    assert tag["tag"] == "WATCH"
    assert tag["stake_eligible"] is False
    assert tag["tag_reason"] == "rush_watch_only_holdout"


def test_pass_is_watch_only_after_holdout() -> None:
    tag = classify_prop_tag(
        market_key="pass_yds",
        position="QB",
        z_over=0.75,
        edge_over=0.07,
        edge_under=-0.07,
        market_joined=True,
        model_mean=275.0,
        line=249.5,
        role_confidence=0.9,
        availability_confidence=0.9,
    )
    assert tag["tag"] == "WATCH"
    assert tag["stake_eligible"] is False


def test_pass_without_market() -> None:
    edge = evaluate_prop_edge(
        model_mean=250.0,
        model_std=40.0,
        line=249.5,
        market_over_price=None,
        market_under_price=None,
        market_key="pass_yds",
        position="QB",
    )
    assert edge["tag"] == "PASS"
    assert edge["tag_reason"] == "no_market"


def test_extreme_z_is_watch_not_play() -> None:
    tag = classify_prop_tag(
        market_key="rec_yds",
        position="WR",
        z_over=1.8,
        edge_over=0.12,
        edge_under=-0.12,
        market_joined=True,
        model_mean=80.0,
        line=64.5,
        role_confidence=0.9,
        availability_confidence=0.9,
    )
    assert tag["tag"] == "WATCH"
    assert tag["size_down"] is True
    assert tag["stake_eligible"] is False


def test_disagreement_gate_blocks_fake_unders() -> None:
    tag = classify_prop_tag(
        market_key="pass_yds",
        position="QB",
        z_over=-1.1,
        edge_over=-0.15,
        edge_under=0.15,
        market_joined=True,
        model_mean=120.0,
        line=252.5,
    )
    assert tag["tag"] == "PASS"
    assert tag["tag_reason"] == "model_market_disagreement"


def test_role_collapse_blocks_under_play_from_crushed_raw() -> None:
    """Featured WR1 raw << line must not become PLAY Under (live W17 failure)."""
    tag = classify_prop_tag(
        market_key="rec_yds",
        position="WR",
        z_over=-0.75,
        edge_over=-0.08,
        edge_under=0.08,
        market_joined=True,
        model_mean=24.0,
        line=41.5,
        role_confidence=0.88,
        availability_confidence=0.9,
        raw_model_mean=12.7,
    )
    assert tag["tag"] == "PASS"
    assert tag["tag_reason"] == "model_role_collapse"


def test_role_collapse_does_not_block_healthy_under() -> None:
    tag = classify_prop_tag(
        market_key="rec_yds",
        position="WR",
        z_over=-0.70,
        edge_over=-0.07,
        edge_under=0.07,
        market_joined=True,
        model_mean=48.0,
        line=58.5,
        role_confidence=0.88,
        availability_confidence=0.9,
        raw_model_mean=46.0,
    )
    assert tag["tag"] == "WATCH"
    assert tag["tag_side"] == "Under"


def test_anytime_td_poisson() -> None:
    p = anytime_td_prob_from_td_mean(0.55)
    assert 0.35 < p < 0.55


def _reliability_inputs(**overrides):
    base = {
        "market_key": "rush_yds",
        "market_joined": True,
        "two_way": True,
        "role_confidence": 0.88,
        "availability_confidence": 0.9,
        "market_shrink": 0.0,
        "calibration_source": "frozen",
        "fallback_used": False,
        "joined_book_count": 2,
    }
    base.update(overrides)
    return base


def test_one_way_atd_returns_none_confidence_not_floor() -> None:
    """C.Sutton-style one-way ATD must not fabricate ~5% next to a large edge."""
    edge = evaluate_prop_edge(
        model_mean=0.4055,
        model_std=0.49,
        line=0.5,
        market_over_price=-150,
        market_under_price=None,
        market_key="anytime_td",
        position="WR",
        role_confidence=0.88,
        availability_confidence=0.9,
        calibration_source="frozen",
        joined_book_count=1,
    )
    assert edge["confidence"] is None
    assert edge["edge_over"] is not None
    assert edge["edge_under"] is None


def test_confidence_independent_of_edge_magnitude() -> None:
    """Identical reliability inputs, different |z| → same confidence."""
    shared = dict(
        model_std=18.0,
        line=64.5,
        market_over_price=-110,
        market_under_price=-110,
        market_key="rec_yds",
        position="WR",
        role_confidence=0.8,
        availability_confidence=0.9,
        calibration_source="frozen",
        joined_book_count=2,
    )
    low_z = evaluate_prop_edge(model_mean=66.0, **shared)
    high_z = evaluate_prop_edge(model_mean=82.0, **shared)
    assert low_z["confidence"] == high_z["confidence"]
    assert abs(low_z["z_over"]) != abs(high_z["z_over"])


def test_reliability_penalties_lower_score() -> None:
    clean = assess_prop_reliability(**_reliability_inputs())
    assert clean is not None
    with_fallback = assess_prop_reliability(**_reliability_inputs(fallback_used=True))
    low_role = assess_prop_reliability(**_reliability_inputs(role_confidence=0.35))
    low_avail = assess_prop_reliability(
        **_reliability_inputs(availability_confidence=0.30)
    )
    assert with_fallback is not None and with_fallback < clean
    assert low_role is not None and low_role < clean
    assert low_avail is not None and low_avail < clean


def test_coverage_scales_with_book_count_no_cliff() -> None:
    one_book = assess_prop_reliability(**_reliability_inputs(joined_book_count=1))
    two_books = assess_prop_reliability(**_reliability_inputs(joined_book_count=2))
    three_books = assess_prop_reliability(**_reliability_inputs(joined_book_count=3))
    one_way = assess_prop_reliability(**_reliability_inputs(two_way=False, joined_book_count=2))
    assert one_book is not None and two_books is not None and three_books is not None
    assert one_book < two_books
    assert two_books == three_books
    assert one_way is not None
    assert one_way == assess_prop_reliability(
        **_reliability_inputs(two_way=False, joined_book_count=1)
    )
    assert two_books - one_book < PROP_COVERAGE_MAX


def test_no_inflation_beyond_base_plus_coverage() -> None:
    score = assess_prop_reliability(**_reliability_inputs())
    assert score is not None
    assert score <= round(PROP_RELIABILITY_BASE + PROP_COVERAGE_MAX, 4)
