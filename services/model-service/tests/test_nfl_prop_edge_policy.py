from src.services.nfl_prop_edge_policy import (
    anytime_td_prob_from_td_mean,
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
    # z = (82-64.5)/18 ≈ 0.97 → PLAY research tag; stake blocked post batch-5
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
    assert edge["tag"] == "PLAY"
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


def test_anytime_td_poisson() -> None:
    p = anytime_td_prob_from_td_mean(0.55)
    assert 0.35 < p < 0.55
