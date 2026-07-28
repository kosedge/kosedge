from __future__ import annotations

from src.services.nfl_player_prop_backtest_scoring import (
    PropBetGrade,
    classify_conviction,
    edge_call_correct,
    grade_actual_outcome,
    grade_prop_bet,
    model_favored_side,
    summarize_grades,
)


def test_model_favored_side_basic() -> None:
    assert model_favored_side(80.0, 65.5) == "over"
    assert model_favored_side(50.0, 65.5) == "under"
    assert model_favored_side(65.5, 65.5) == "push_no_side"


def test_grade_actual_outcome_basic() -> None:
    assert grade_actual_outcome(80.0, 65.5) == "over"
    assert grade_actual_outcome(50.0, 65.5) == "under"
    assert grade_actual_outcome(4.0, 4.0) == "push"


def test_classify_conviction_scales_with_std() -> None:
    # Same 10-yard gap from the line, tighter std -> higher conviction.
    tight = classify_conviction(model_mean=85.0, line=75.0, model_std=5.0)
    wide = classify_conviction(model_mean=85.0, line=75.0, model_std=40.0)
    assert tight == "high"
    assert wide == "low"


def test_grade_prop_bet_win_when_model_and_actual_agree() -> None:
    grade = grade_prop_bet(
        model_mean=90.0,
        model_std=15.0,
        line=70.5,
        actual=95.0,
        market_over_price=-115,
        market_under_price=-105,
    )
    assert grade.side == "over"
    assert grade.outcome == "win"
    assert grade.conviction == "high"
    assert grade.edge is not None
    assert grade.market_implied_prob is not None


def test_grade_prop_bet_loss_when_model_and_actual_disagree() -> None:
    grade = grade_prop_bet(
        model_mean=90.0,
        model_std=15.0,
        line=70.5,
        actual=40.0,
        market_over_price=-115,
        market_under_price=-105,
    )
    assert grade.side == "over"
    assert grade.outcome == "loss"


def test_grade_prop_bet_push_when_actual_equals_line() -> None:
    grade = grade_prop_bet(model_mean=90.0, model_std=15.0, line=70.0, actual=70.0)
    assert grade.outcome == "push"


def test_grade_prop_bet_push_no_side_when_mean_equals_line() -> None:
    grade = grade_prop_bet(model_mean=70.0, model_std=15.0, line=70.0, actual=95.0)
    assert grade.side == "push_no_side"
    assert grade.outcome == "push"
    assert grade.edge is None


def test_grade_prop_bet_without_market_price_has_no_edge_but_still_grades() -> None:
    grade = grade_prop_bet(model_mean=90.0, model_std=15.0, line=70.5, actual=95.0)
    assert grade.outcome == "win"
    assert grade.edge is None
    assert grade.market_implied_prob is None
    assert 0.0 <= grade.model_implied_prob <= 1.0


def test_edge_call_correct_none_when_no_edge_claimed() -> None:
    assert edge_call_correct(None, "win") is None
    assert edge_call_correct(-0.05, "win") is None
    assert edge_call_correct(0.10, "push") is None


def test_edge_call_correct_matches_outcome_when_edge_claimed() -> None:
    assert edge_call_correct(0.10, "win") is True
    assert edge_call_correct(0.10, "loss") is False


def test_summarize_grades_win_rates_and_conviction_split() -> None:
    grades = [
        PropBetGrade("over", "win", "high", 0.10, 0.65, 0.55),
        PropBetGrade("over", "win", "high", 0.08, 0.62, 0.55),
        PropBetGrade("over", "loss", "high", 0.05, 0.58, 0.55),
        PropBetGrade("under", "loss", "low", 0.02, 0.52, 0.50),
        PropBetGrade("under", "win", "low", 0.01, 0.51, 0.50),
        PropBetGrade("push_no_side", "push", "low", None, 0.5, None),
    ]
    summary = summarize_grades(grades)
    assert summary["n_total"] == 6
    assert summary["n_pushes"] == 1
    assert summary["overall"]["n"] == 5
    assert summary["overall"]["wins"] == 3
    assert summary["high_conviction"]["n"] == 3
    assert summary["high_conviction"]["wins"] == 2
    assert summary["low_conviction"]["n"] == 2
    assert summary["low_conviction"]["wins"] == 1
    assert summary["edge_call_accuracy"]["n"] == 5
    assert summary["edge_call_accuracy"]["correct"] == 3


def test_summarize_grades_empty_input_is_safe() -> None:
    summary = summarize_grades([])
    assert summary["n_total"] == 0
    assert summary["overall"] is None
    assert summary["high_conviction"] is None
    assert summary["low_conviction"] is None
    assert summary["edge_call_accuracy"] is None
