"""Evaluator scaffolding tests: freeze-before-join, market rules, metrics."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.services.nfl_odds_comparison_harness import UNBOUND_PROBABILITY_LINE
from src.services.nfl_t5107u.builder import build_forecasts
from src.services.nfl_t5107u.evaluator import (
    BOOT_B,
    BOOT_SEED,
    COS_ONE_RUN_BIND,
    EvalRefuse,
    FrozenCohort,
    bootstrap_ci,
    clip_logloss_p,
    delta_mae,
    freeze_forecast_cohort,
    home_margin_from_handicap,
    kickoff_minus_minutes,
    multiplicative_devig,
    paired_mae,
    refuse_invented_ats_ou_probs,
    reporting_class,
    run_eval_score,
    season_exclusion_hold,
    select_market_quotes,
)
from src.services.nfl_t5107u.if_control import IF_TIP
from src.services.nfl_t5107u.q2 import Game


def _target():
    return Game(
        season=2020,
        week=1,
        game_id="2020_01_HOU_KC",
        home="KC",
        away="HOU",
        kickoff_utc=datetime(2020, 9, 10, 20, 20, tzinfo=timezone.utc),
    )


def _forecast_payload():
    return build_forecasts(
        [_target()],
        history=[],
        archived_if={
            "2020_01_HOU_KC": {
                "if_tip": IF_TIP,
                "if_forecast_label": "independent_fair",
                "if_margin_mu": 6.0,
            }
        },
    )


def test_freeze_hashes_before_outcome_join():
    payload = _forecast_payload()
    frozen = freeze_forecast_cohort(payload)
    assert frozen.sealed_before_outcome_join is True
    assert frozen.n == 1
    assert frozen.forecast_sha256
    assert frozen.cohort_sha256
    dirty = dict(payload)
    dirty["forecasts"] = [{**payload["forecasts"][0], "home_score": 27, "actual_margin": 10}]
    with pytest.raises(EvalRefuse, match="already joined"):
        freeze_forecast_cohort(dirty)


def test_exec_score_refused_without_cos_bind():
    frozen = freeze_forecast_cohort(_forecast_payload())
    with pytest.raises(EvalRefuse, match="Alex preflight"):
        run_eval_score(frozen, {"2020_01_HOU_KC": {"season": 2020, "home_score": 34, "away_score": 20}})
    with pytest.raises(EvalRefuse, match="Alex preflight"):
        run_eval_score(
            frozen,
            {"2020_01_HOU_KC": {"season": 2020, "home_score": 34, "away_score": 20}},
            exec_bind="please",
        )


def test_hash_mismatch_refuses_even_if_bind_forged():
    payload = _forecast_payload()
    frozen = freeze_forecast_cohort(payload)
    tampered = FrozenCohort(
        forecast_sha256="0" * 64,
        cohort_sha256=frozen.cohort_sha256,
        game_ids=frozen.game_ids,
        n=frozen.n,
        sealed_before_outcome_join=True,
        payload=payload,
    )
    with pytest.raises(EvalRefuse, match="hash mismatch"):
        run_eval_score(
            tampered,
            {"2020_01_HOU_KC": {"season": 2020, "home_score": 1, "away_score": 0}},
            exec_bind=COS_ONE_RUN_BIND,
        )


def test_cutoff_is_kickoff_minus_60_and_stale_quote_dropped():
    kickoff = "2020-09-10T20:20:00Z"
    cutoff = kickoff_minus_minutes(kickoff)
    assert cutoff.isoformat().replace("+00:00", "Z") == "2020-09-10T19:20:00Z"
    games = [
        {
            "game_id": "2020_01_HOU_KC",
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home_team": "KC",
            "away_team": "HOU",
            "kickoff": kickoff,
        }
    ]
    quotes = [
        {
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home": "Kansas City Chiefs",
            "away": "Houston Texans",
            "book": "draftkings",
            "market": "spreads",
            "spread_home": -7.5,
            "price_home": -110,
            "captured_at": "2020-09-10T19:00:00Z",
            "source": "synthetic",
            "provenance": "synthetic",
        },
        {
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home": "Kansas City Chiefs",
            "away": "Houston Texans",
            "book": "fanduel",
            "market": "spreads",
            "spread_home": -3.5,
            "price_home": -110,
            "captured_at": "2020-09-09T18:00:00Z",
            "source": "synthetic",
            "provenance": "synthetic",
        },
        {
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home": "Kansas City Chiefs",
            "away": "Houston Texans",
            "book": "betmgm",
            "market": "spreads",
            "spread_home": -6.5,
            "price_home": -110,
            "captured_at": "2020-09-10T19:00:00Z",
            "source": "synthetic",
            "provenance": "synthetic",
        },
    ]
    result = select_market_quotes(quotes, games)
    point = result["points"][0]
    assert point["market_margin"] == pytest.approx(7.5)
    assert point["book_count"] == 1
    reasons = {row["reason"] for row in result["excluded"]}
    assert "quote_too_old" in reasons
    assert "book_not_benchmark" in reasons
    assert result["book_disclosure"]["one_book_games"] == 1


def test_naive_timestamp_refused_and_post_cutoff_dropped():
    games = [
        {
            "game_id": "2020_01_HOU_KC",
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home_team": "KC",
            "away_team": "HOU",
            "kickoff": "2020-09-10T20:20:00Z",
        }
    ]
    quotes = [
        {
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home": "KC",
            "away": "HOU",
            "book": "fanduel",
            "market": "spreads",
            "spread_home": -7.0,
            "captured_at": "2020-09-10T19:00:00",
            "source": "synthetic",
            "provenance": "synthetic",
        },
        {
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home": "KC",
            "away": "HOU",
            "book": "fanduel",
            "market": "spreads",
            "spread_home": -1.0,
            "captured_at": "2020-09-10T19:30:00Z",
            "source": "synthetic",
            "provenance": "synthetic",
        },
    ]
    result = select_market_quotes(quotes, games)
    reasons = {row["reason"] for row in result["excluded"]}
    assert "unresolvable_timestamp" in reasons
    assert "post_cutoff" in reasons
    assert result["points"][0]["market_margin"] is None


def test_multiplicative_devig_and_home_margin_sign():
    assert home_margin_from_handicap(-7.5) == pytest.approx(7.5)
    assert home_margin_from_handicap(3.0) == pytest.approx(-3.0)
    assert multiplicative_devig(0.55, 0.50) == pytest.approx(0.55 / 1.05)
    with pytest.raises(EvalRefuse):
        multiplicative_devig(0.0, 0.5)


def test_p_bind_refuses_unbound_probability_line():
    games = [
        {
            "game_id": "2020_01_HOU_KC",
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home_team": "KC",
            "away_team": "HOU",
            "kickoff": "2020-09-10T20:20:00Z",
        }
    ]
    quotes = [
        {
            "event_id": "evt-1",
            "season": 2020,
            "game_date": "2020-09-10",
            "home": "KC",
            "away": "HOU",
            "book": "draftkings",
            "market": "spreads",
            "spread_home": -7.5,
            "price_home": -110,
            "captured_at": "2020-09-10T19:00:00Z",
            "source": "synthetic",
            "provenance": "synthetic",
        }
    ]
    forecasts = [
        {
            "game_id": "2020_01_HOU_KC",
            "markets": {"spread": {"prediction": -3.5, "p_home_cover": 0.58}},
        }
    ]
    result = select_market_quotes(quotes, games, forecasts=forecasts)
    assert result["points"][0]["p_compare"] == UNBOUND_PROBABILITY_LINE
    assert result["points"][0]["p_home_fair"] is None


def test_metrics_bootstrap_holds_and_no_ats_invention():
    assert paired_mae([2.0, -4.0]) == pytest.approx(3.0)
    assert delta_mae([1.0, 3.0], [2.0, 2.0]) == pytest.approx(2.0 - 2.0)
    ci = bootstrap_ci([-1.0, 0.5, 0.2, -0.1])
    assert ci["B"] == BOOT_B
    assert ci["seed"] == BOOT_SEED
    assert ci["verdict"] in {"INCONCLUSIVE", "CI_EXCLUDES_ZERO"}
    with pytest.raises(EvalRefuse, match="frozen"):
        bootstrap_ci([1.0, 2.0], seed=1)
    assert reporting_class(99) == "DESCRIPTIVE_ONLY"
    assert reporting_class(100) == "REPORTABLE_NOT_AUTO_PASS"
    hold = season_exclusion_hold(100, 31)
    assert hold["hold"] is True
    assert hold["hold_threshold"] == 0.30
    clipped, flagged = clip_logloss_p(0.0)
    assert flagged is True
    assert clipped == pytest.approx(1.0 / 8000.0)
    with pytest.raises(EvalRefuse, match="ATS/OU"):
        refuse_invented_ats_ou_probs([0.1, 0.2])
