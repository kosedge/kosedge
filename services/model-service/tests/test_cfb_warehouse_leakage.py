"""Zero-leakage contract tests — future features must not pass these."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.backtest import grade_row, run_harness
from src.services.cfb_warehouse.leakage import (
    LEAKAGE_RULE,
    assert_available_before_kickoff,
    era_tag,
    filter_available,
    is_available_before_kickoff,
)


def test_era_tags() -> None:
    assert era_tag(2001) == "pre-2002"
    assert era_tag(2005) == "2002-09"
    assert era_tag(2014) == "2010-17"
    assert era_tag(2019) == "2018-21"
    assert era_tag(2024) == "2022-present"


def test_kickoff_rule_rejects_same_timestamp() -> None:
    kick = datetime(2024, 9, 7, 16, 0, tzinfo=timezone.utc)
    assert is_available_before_kickoff(
        available_at=datetime(2024, 9, 7, 15, 59, tzinfo=timezone.utc),
        kickoff=kick,
    )
    assert not is_available_before_kickoff(available_at=kick, kickoff=kick)
    with pytest.raises(ValueError, match="leakage"):
        assert_available_before_kickoff(
            available_at="2024-09-07T16:00:00+00:00",
            kickoff="2024-09-07T16:00:00+00:00",
            feature_name="final_season_rating",
        )


def test_end_of_year_rating_nulled_for_week_1() -> None:
    """Toy feature builder: season-final SOS must not feed Week 1 of the same year."""
    rows = [
        {
            "feature": "end_of_year_sos",
            "available_at": "2024-12-20T00:00:00+00:00",
            "feature_week": 15,
        },
        {
            "feature": "prior_year_sp",
            "available_at": "2023-12-20T00:00:00+00:00",
            "feature_week": 15,
        },
    ]
    kept = filter_available(
        rows,
        kickoff="2024-08-31T16:00:00+00:00",
        game_date="2024-08-31",
        game_week=1,
    )
    assert [r["feature"] for r in kept] == ["prior_year_sp"]


def test_week_fallback_matches_nfl_kav_strictness() -> None:
    assert is_available_before_kickoff(available_at=None, feature_week=4, game_week=5)
    assert not is_available_before_kickoff(available_at=None, feature_week=5, game_week=5)
    assert not is_available_before_kickoff(available_at=None, feature_week=6, game_week=5)


def test_unprovable_availability_is_unsafe() -> None:
    assert not is_available_before_kickoff(available_at=None, kickoff=None, game_date=None)


def test_harness_rejects_future_model_fair() -> None:
    game = {
        "game_id": "toy-1",
        "season": 2024,
        "week": 1,
        "kickoff": "2024-08-31T16:00:00+00:00",
        "game_date": "2024-08-31",
        "home_team_id": "UGA",
        "away_team_id": "CLEM",
        "home_score": 34,
        "away_score": 3,
        "close_spread_home": -14.0,
        "close_total": 48.5,
    }
    with pytest.raises(ValueError, match="leakage"):
        run_harness(
            [game],
            fairs={
                "toy-1": {
                    "model_spread_home": -10.0,
                    "available_at": "2024-12-15T00:00:00+00:00",
                }
            },
        )


def test_harness_placeholder_fair_still_emits_result_columns() -> None:
    game = {
        "game_id": "toy-2",
        "season": 2024,
        "week": 1,
        "kickoff": "2024-08-31T16:00:00+00:00",
        "game_date": "2024-08-31",
        "home_team_id": "TEX",
        "away_team_id": "OSU",
        "home_score": 31,
        "away_score": 28,
        "close_spread_home": -3.0,
        "open_spread_home": -2.5,
        "close_total": 55.0,
    }
    rows = run_harness([game], fairs={})
    assert len(rows) == 1
    assert rows[0]["model_fair_present"] is False
    assert rows[0]["margin"] == 3.0
    assert rows[0]["su_home"] is True
    assert rows[0]["close_spread_home"] == -3.0
    assert LEAKAGE_RULE == "strictly_before_kickoff"


def test_legal_prior_year_fair_grades() -> None:
    game = {
        "game_id": "toy-3",
        "season": 2024,
        "week": 1,
        "kickoff": "2024-08-31T16:00:00+00:00",
        "game_date": "2024-08-31",
        "home_team_id": "UGA",
        "away_team_id": "CLEM",
        "home_score": 34,
        "away_score": 10,
        "close_spread_home": -14.0,
        "open_spread_home": -13.0,
    }
    row = grade_row(
        game,
        model_spread_home=-16.0,
        model_available_at="2024-08-01T00:00:00+00:00",
    )
    assert row["spread_error"] == -2.0
    assert row["model_fair_present"] is True
    assert row["ats_flag"] is True  # model more home-favored; home covered 24 vs -14
