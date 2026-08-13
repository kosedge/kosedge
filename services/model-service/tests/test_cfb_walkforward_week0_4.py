"""Leakage + smoke tests for CFB Week 0–4 walk-forward harness."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.walkforward import (
    build_program_priors,
    lookup_efficiency,
    model_fair,
    signed_clv,
    summarize,
    walkforward_games,
    week_band,
    wilson_interval,
)


def test_week_bands() -> None:
    assert week_band(0) == "w0_1"
    assert week_band(1) == "w0_1"
    assert week_band(4) == "w2_4"
    assert week_band(5) == "w5_plus"


def test_week1_fair_is_prior_only_and_ignores_same_week_epa() -> None:
    spread, status, drivers = model_fair(
        week=1,
        home_prior=10.0,
        away_prior=0.0,
        home_eff=99.0,
        away_eff=-99.0,
        home_cold=True,
        away_cold=True,
        neutral=True,
    )
    assert status == "ok"
    assert drivers["blend"] == "prior_only"
    assert spread == pytest.approx(-10.0)


def test_week3_missing_efficiency_is_incomplete_not_zero() -> None:
    spread, status, _ = model_fair(
        week=3,
        home_prior=8.0,
        away_prior=0.0,
        home_eff=None,
        away_eff=None,
        home_cold=False,
        away_cold=False,
        neutral=True,
    )
    assert spread is None
    assert status == "incomplete_efficiency"


def test_week3_cold_start_is_incomplete() -> None:
    spread, status, _ = model_fair(
        week=3,
        home_prior=8.0,
        away_prior=0.0,
        home_eff=0.0,
        away_eff=0.0,
        home_cold=True,
        away_cold=False,
        neutral=True,
    )
    assert spread is None
    assert status == "incomplete_efficiency"


def test_efficiency_lookup_rejects_same_week_and_future() -> None:
    idx = {
        (2024, 3, "UGA"): {
            "team_id": "UGA",
            "as_of_week": 3,
            "feature_week": 3,
            "max_week_included": 3,
            "off_epa_adj": 0.4,
            "def_epa_adj": -0.2,
            "cold_start": False,
        }
    }
    row, why = lookup_efficiency(
        idx,
        season=2024,
        week=3,
        team="UGA",
        kickoff="2024-09-14T16:00:00+00:00",
        game_date="2024-09-14",
    )
    assert row is None
    assert why == "leakage"

    idx[(2024, 3, "UGA")]["feature_week"] = 2
    idx[(2024, 3, "UGA")]["max_week_included"] = 2
    row, why = lookup_efficiency(
        idx,
        season=2024,
        week=3,
        team="UGA",
        kickoff="2024-09-14T16:00:00+00:00",
        game_date="2024-09-14",
    )
    assert row is not None
    assert why in {"week_fallback", "week_fallback_ts_ignored", "timestamp"}


def test_program_prior_excludes_same_year() -> None:
    finals = [
        {"season": 2023, "team_id": "UGA", "off_epa_adj": 0.2, "def_epa_adj": -0.1},
        {"season": 2024, "team_id": "UGA", "off_epa_adj": 9.0, "def_epa_adj": -9.0},
    ]
    priors = build_program_priors(finals, [2024])
    assert (2024, "UGA") in priors
    assert 2024 not in priors[(2024, "UGA")]["seasons"]
    assert priors[(2024, "UGA")]["net_epa"] == pytest.approx(0.3, abs=0.01)


def test_walkforward_skips_silent_zero_and_flags_thin() -> None:
    games = [
        {
            "game_id": "g1",
            "season": 2024,
            "week": 1,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
            "kickoff": "2024-08-31T16:00:00+00:00",
            "game_date": "2024-08-31",
            "neutral": True,
            "home_score": 34,
            "away_score": 3,
            "close_spread_home": -13.5,
            "open_spread_home": -13.5,
            "era_tag": "2022-present",
        }
    ]
    priors = {
        (2024, "UGA"): {"points": 12.0, "seasons": [2023]},
        (2024, "CLEM"): {"points": 4.0, "seasons": [2023]},
    }
    rows = walkforward_games(games, priors=priors, eff_idx={})
    assert rows[0]["fair_status"] == "ok"
    assert rows[0]["model_spread_home"] == pytest.approx(-8.0)
    assert rows[0]["spread_error"] == pytest.approx(-8.0 - -13.5)
    summary = summarize(rows)
    assert summary["by_week_band"]["w0_1"]["sample_flag"] in {"thin", "exploratory"}
    assert summary["overall"]["n_close"] == 1


def test_signed_clv_and_wilson() -> None:
    # Model more home than open (-14 vs -10); close moved to -13 → toward model.
    assert signed_clv(-14.0, -10.0, -13.0) > 0
    lo, hi = wilson_interval(6, 10)
    assert 0.0 <= lo <= 0.6 <= hi <= 1.0
