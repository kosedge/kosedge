"""Focused tests for B2-PACE-v1 challenger (unit correction only)."""

from __future__ import annotations

import inspect
from datetime import date

import polars as pl
import pytest

from ncaam_lab.fair_b2 import compute_fair_b2
from ncaam_lab.fair_b2_pace_v1 import (
    CANDIDATE_ID,
    ELIGIBLE_COL,
    FAIR_COL,
    INCUMBENT_CANDIDATE_ID,
    METHOD_ID,
    compute_fair_b2_pace_v1,
    scalar_fair_home_margin,
    select_fair_candidate,
)
from ncaam_lab.materialize import materialize_lab_fair
from ncaam_lab.protocol import DEFAULT_HCA


def _base_games(**overrides) -> pl.DataFrame:
    row = {
        "event_id": "e1",
        "tip_date": date(2022, 12, 10),
        "adjem_home": 30.0,
        "adjem_away": 10.0,
        "adjt_home": 67.5,
        "adjt_away": 67.5,
        "kenpom_as_of_home": date(2022, 12, 4),
        "kenpom_as_of_away": date(2022, 12, 4),
        "adjoe_home": 110.0,
        "adjde_home": 90.0,
        "adjoe_away": 100.0,
        "adjde_away": 100.0,
    }
    row.update(overrides)
    return pl.DataFrame([row])


def test_example_conversion_20_adj_diff_67_5_poss() -> None:
    # 20 * (67.5/100) + 2.8696 = 16.3696
    got = scalar_fair_home_margin(
        adjem_home=30.0,
        adjem_away=10.0,
        adjt_home=67.5,
        adjt_away=67.5,
        hca=2.8696,
    )
    assert got == pytest.approx(16.3696)


def test_positive_and_negative_adjem_signs() -> None:
    pos = scalar_fair_home_margin(
        adjem_home=30.0, adjem_away=10.0, adjt_home=67.5, adjt_away=67.5, hca=2.8696
    )
    neg = scalar_fair_home_margin(
        adjem_home=10.0, adjem_away=30.0, adjt_home=67.5, adjt_away=67.5, hca=2.8696
    )
    assert pos is not None and neg is not None
    assert pos == pytest.approx(16.3696)
    assert neg == pytest.approx(-10.6304)
    # Sign convention: positive => home favored (same as incumbent fair_spread_home)
    games = _base_games()
    out = compute_fair_b2_pace_v1(compute_fair_b2(games, hca=2.8696), hca=2.8696)
    assert out[FAIR_COL][0] == pytest.approx(16.3696)
    assert out["fair_spread_home"][0] == pytest.approx(22.8696)


def test_hca_added_after_not_before_possession_scaling() -> None:
    # If HCA were added before scaling: (20+2.8696)*0.675 = 15.4370 — must NOT match.
    wrong_before = (20.0 + 2.8696) * 0.675
    right_after = 20.0 * 0.675 + 2.8696
    got = scalar_fair_home_margin(
        adjem_home=30.0, adjem_away=10.0, adjt_home=67.5, adjt_away=67.5, hca=2.8696
    )
    assert got == pytest.approx(right_after)
    assert got != pytest.approx(wrong_before)


def test_adjem_prescale_clip_pm30() -> None:
    # Raw diff 45 → clip to 30 → 30*(70/100)+HCA
    got = scalar_fair_home_margin(
        adjem_home=50.0, adjem_away=5.0, adjt_home=70.0, adjt_away=70.0, hca=2.8696
    )
    assert got == pytest.approx(30.0 * 0.70 + 2.8696)


def test_final_game_margin_clip_pm28() -> None:
    # Large scaled margin must clip at ±28 (tempo high enough after AdjEM clip).
    got = scalar_fair_home_margin(
        adjem_home=40.0, adjem_away=0.0, adjt_home=90.0, adjt_away=90.0, hca=2.8696
    )
    # raw = clip(40,30)*0.9 + 2.8696 = 29.8696 → clip 28
    assert got == pytest.approx(28.0)


def test_missing_home_or_away_adjt_fails_closed() -> None:
    games = _base_games(adjt_home=None)
    out = compute_fair_b2_pace_v1(games, hca=2.8696)
    assert out[FAIR_COL][0] is None
    assert out[ELIGIBLE_COL][0] is False

    games2 = _base_games(adjt_away=None)
    out2 = compute_fair_b2_pace_v1(games2, hca=2.8696)
    assert out2[FAIR_COL][0] is None


def test_post_tip_inputs_rejected() -> None:
    games = _base_games(kenpom_as_of_home=date(2022, 12, 11))  # after tip
    out = compute_fair_b2_pace_v1(games, hca=2.8696)
    assert out[FAIR_COL][0] is None
    assert out[ELIGIBLE_COL][0] is False


def test_settled_not_emitted() -> None:
    out = compute_fair_b2_pace_v1(_base_games(), hca=2.8696)
    assert "SETTLED" not in out["continuity_state_b2_pace_v1"].to_list()
    assert out["continuity_state_b2_pace_v1"][0] == "PRIOR"


def test_prior_and_unknown_accepted_under_existing_rules() -> None:
    prior = compute_fair_b2_pace_v1(_base_games(), hca=2.8696)
    assert prior["continuity_state_b2_pace_v1"][0] == "PRIOR"
    # Missing as-of → UNKNOWN continuity; fair fails closed (no valid PIT)
    unknown = compute_fair_b2_pace_v1(_base_games(kenpom_as_of_home=None), hca=2.8696)
    assert unknown["continuity_state_b2_pace_v1"][0] == "UNKNOWN"
    assert unknown[FAIR_COL][0] is None


def test_market_odds_cannot_enter_challenger_formula() -> None:
    src = inspect.getsource(compute_fair_b2_pace_v1)
    banned_cols = [
        "b1_consensus",
        "close_spread",
        "open_spread",
        "consensus_close",
        "implied_prob",
        "close_total",
        "open_total",
        "moneyline",
    ]
    for token in banned_cols:
        assert token not in src
    assert 'pl.col("b1' not in src
    assert "pl.col('b1" not in src


def test_candidate_selection_explicit_no_default_replace() -> None:
    games = compute_fair_b2(_base_games(), hca=2.8696)
    games = compute_fair_b2_pace_v1(games, hca=2.8696)
    # Incumbent fair remains present and distinct
    assert games["fair_spread_home"][0] == pytest.approx(22.8696)
    assert games[FAIR_COL][0] == pytest.approx(16.3696)
    sel = select_fair_candidate(games, CANDIDATE_ID)
    assert sel["selected_fair_candidate_id"][0] == CANDIDATE_ID
    assert sel["selected_fair_spread_home"][0] == pytest.approx(16.3696)
    sel0 = select_fair_candidate(games, INCUMBENT_CANDIDATE_ID)
    assert sel0["selected_fair_candidate_id"][0] == INCUMBENT_CANDIDATE_ID
    assert sel0["selected_fair_spread_home"][0] == pytest.approx(22.8696)
    with pytest.raises(ValueError):
        select_fair_candidate(games, "")  # no silent default


def test_incumbent_outputs_unchanged_when_challenger_attached() -> None:
    games = _base_games()
    c0 = compute_fair_b2(games, hca=DEFAULT_HCA)
    both = compute_fair_b2_pace_v1(c0, hca=DEFAULT_HCA)
    for col in [
        "fair_spread_home",
        "hca_applied",
        "fair_spread_method",
        "continuity_state",
        "fair_ml_home",
        "fair_total",
    ]:
        assert c0[col].to_list() == both[col].to_list()


def test_materialize_still_calls_only_incumbent_engine() -> None:
    src = inspect.getsource(materialize_lab_fair)
    assert "compute_fair_b2(" in src
    assert "compute_fair_b2_pace_v1(" not in src
    assert "from ncaam_lab.fair_b2_pace_v1" not in src
    # Comment may mention the challenger ID as a warning; call site must not.


def test_default_hca_matches_frozen_value() -> None:
    assert DEFAULT_HCA == pytest.approx(2.8696)
    assert CANDIDATE_ID == "B2-PACE-v1"
    assert METHOD_ID == "kenpom_adjem_pit_tempo_plus_game_hca_v1"
