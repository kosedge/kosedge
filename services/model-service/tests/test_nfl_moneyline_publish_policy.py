"""Pure-fn tests for ML EV gate + publish policy."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_moneyline_publish_policy import (
    ML_MIN_EV,
    american_to_decimal,
    american_to_implied_prob,
    ev_per_unit,
    publish_moneyline_tag,
)
from src.services.nfl_side_total_publish_policy import (
    is_market_side_disagreement,
    publish_tag,
)


def test_american_converters():
    assert abs(american_to_decimal(-110) - (1 + 100 / 110)) < 1e-9
    assert abs(american_to_decimal(150) - 2.5) < 1e-9
    assert abs(american_to_implied_prob(-110) - (110 / 210)) < 1e-9
    assert abs(american_to_implied_prob(150) - (100 / 250)) < 1e-9


def test_ev_per_unit_plus_ev_on_plus_money():
    # 55% true win prob at +150 → EV = 0.55*1.5 - 0.45 = 0.375
    ev = ev_per_unit(model_win_prob=0.55, american_odds=150)
    assert abs(ev - 0.375) < 1e-9


def test_ml_play_requires_spread_play_and_ev_bar():
    blocked = publish_moneyline_tag(
        spread_tag="PASS",
        spread_stake_eligible=False,
        model_win_prob=0.6,
        offered_american=-110,
    )
    assert blocked["tag"] == "PASS"
    assert blocked["reason"] == "spread_not_play"

    thin = publish_moneyline_tag(
        spread_tag="PLAY",
        spread_stake_eligible=True,
        model_win_prob=0.53,  # barely above -110 breakeven ~52.38%
        offered_american=-110,
    )
    assert thin["tag"] == "PASS"
    assert thin["reason"] == "ml_ev_below_bar"
    assert thin["ev"] < ML_MIN_EV

    clear = publish_moneyline_tag(
        spread_tag="PLAY",
        spread_stake_eligible=True,
        model_win_prob=0.58,
        offered_american=-110,
    )
    assert clear["tag"] == "PLAY"
    assert clear["stake_eligible"] is True
    assert clear["ev"] >= ML_MIN_EV


def test_ml_respects_red_product_gate():
    out = publish_moneyline_tag(
        spread_tag="PLAY",
        spread_stake_eligible=True,
        model_win_prob=0.7,
        offered_american=120,
        product_gate_status="RED",
    )
    assert out["tag"] == "PASS"
    assert out["reason"] == "product_gate_red"


def test_preseason_blocks_season_play_tags():
    out = publish_tag(
        market="spread",
        abs_edge=3.5,
        product_gate_status="YELLOW",
        season_type="PRE",
    )
    assert out["tag"] == "PASS"
    assert out["reason"] == "preseason_info_desk"
    assert out["stake_eligible"] is False

    ml = publish_moneyline_tag(
        spread_tag="PLAY",
        spread_stake_eligible=True,
        model_win_prob=0.7,
        offered_american=120,
        season_type="PRE",
    )
    assert ml["tag"] == "PASS"
    assert ml["reason"] == "preseason_info_desk"


def test_totals_sides_only_launch():
    out = publish_tag(
        market="total",
        abs_edge=2.7,
        product_gate_status="GREEN",
        season_type="REG",
    )
    assert out["tag"] == "PASS"
    assert out["reason"] == "totals_sides_only_launch"


def test_market_side_disagreement_blocks_spread_play():
    assert is_market_side_disagreement(
        model_spread_home=-3.07, market_spread_home=2.6
    )
    out = publish_tag(
        market="spread",
        abs_edge=5.57,
        product_gate_status="GREEN",
        season_type="REG",
        model_spread_home=-3.07,
        market_spread_home=2.6,
    )
    assert out["tag"] == "PASS"
    assert out["reason"] == "market_side_disagreement"
    assert out["stake_eligible"] is False
