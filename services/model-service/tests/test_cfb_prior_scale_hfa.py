"""Holdout scale/HFA: split years, scale > 0, no EPA, smoke fit."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.scale_hfa import (
    HOLDOUT_YEARS,
    TRAIN_YEARS,
    collect_eligible,
    decide_adopt,
    fit_scale_hfa,
    run_holdout_calibration,
    scaled_spread,
)


def test_train_holdout_years_do_not_overlap() -> None:
    assert set(TRAIN_YEARS).isdisjoint(HOLDOUT_YEARS)
    assert 2024 in HOLDOUT_YEARS and 2023 in TRAIN_YEARS


def test_scale_positive_and_hfa_band() -> None:
    # Home favored by ~14 when prior_diff=10 → scale ~1.4, HFA ~0 (neutral).
    rows = []
    for i, diff in enumerate((4.0, 8.0, 12.0, -6.0, 10.0, 2.0)):
        close = -1.4 * diff  # implied scale 1.4, HFA 0, all neutral
        rows.append(
            {
                "game_id": f"g{i}",
                "season": 2021,
                "week": 1,
                "neutral": True,
                "close_spread_home": close,
                "prior_diff": diff,
                "home_team_id": "UGA",
                "away_team_id": "CLEM",
            }
        )
    fit = fit_scale_hfa(rows, scale_step=0.1, hfa_step=0.5)
    assert fit["scale"] > 0
    assert 0.0 <= fit["hfa"] <= 4.0
    assert abs(fit["scale"] - 1.4) <= 0.15


def test_overlap_years_raise() -> None:
    with pytest.raises(ValueError, match="overlap"):
        run_holdout_calibration([], {}, train_years=[2023, 2024], holdout_years=[2024, 2025])


def test_collect_excludes_missing_prior_and_close() -> None:
    games = [
        {
            "game_id": "a",
            "season": 2022,
            "week": 1,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
            "close_spread_home": -13.5,
            "neutral": True,
        },
        {
            "game_id": "b",
            "season": 2022,
            "week": 1,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
            "close_spread_home": None,
            "neutral": True,
        },
        {
            "game_id": "c",
            "season": 2022,
            "week": 1,
            "home_team_id": "UGA",
            "away_team_id": "BALL",
            "close_spread_home": -21.0,
            "neutral": False,
        },
    ]
    priors = {
        (2022, "UGA"): {"points": 12.0},
        (2022, "CLEM"): {"points": 4.0},
    }
    rows, counts = collect_eligible(games, priors, years=[2022], max_week=4)
    assert counts["excluded_no_close"] == 1
    assert counts["excluded_no_prior"] == 1
    assert counts["eligible"] == 1
    assert rows[0]["prior_diff"] == pytest.approx(8.0)


def test_scaled_spread_sign_home_favored_negative() -> None:
    # Better home prior → negative home spread.
    assert scaled_spread(10.0, scale=1.5, hfa=2.0, neutral=False) < 0
    # Neutral drops HFA.
    with_hfa = scaled_spread(0.0, scale=1.0, hfa=2.0, neutral=False)
    neutral = scaled_spread(0.0, scale=1.0, hfa=2.0, neutral=True)
    assert with_hfa == pytest.approx(-2.0)
    assert neutral == pytest.approx(0.0)


def test_adopt_requires_clear_holdout_mae_margin() -> None:
    ok, _ = decide_adopt(
        baseline_holdout_mae=9.0,
        calibrated_holdout_mae=8.0,
        holdout_n=200,
        scale=1.8,
    )
    assert ok is True
    no, reason = decide_adopt(
        baseline_holdout_mae=9.0,
        calibrated_holdout_mae=8.7,
        holdout_n=200,
        scale=1.8,
    )
    assert no is False
    assert "below_margin" in reason


def test_holdout_not_used_in_fit() -> None:
    """Train-only grid: a holdout-only outlier must not change fitted scale."""
    train = [
        {
            "game_id": f"t{i}",
            "season": 2021,
            "week": 1,
            "neutral": True,
            "close_spread_home": -2.0 * d,
            "prior_diff": d,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
        }
        for i, d in enumerate((3.0, 6.0, 9.0, -3.0, 5.0))
    ]
    fit = fit_scale_hfa(train, scale_step=0.1, hfa_step=0.5)
    assert abs(fit["scale"] - 2.0) <= 0.15
    # Sanity: holdout years constant is disjoint.
    assert 2025 not in TRAIN_YEARS


def _toy_game(gid: str, season: int, week: int, close: float, home_pts: float, away_pts: float) -> dict:
    return {
        "game_id": gid,
        "season": season,
        "week": week,
        "home_team_id": "UGA",
        "away_team_id": "CLEM",
        "neutral": True,
        "close_spread_home": close,
        "open_spread_home": close,
        "home_score": 31.0,
        "away_score": 10.0,
        "prior_home": home_pts,
        "prior_away": away_pts,
    }


def test_smoke_eval_tiny_subset() -> None:
    """End-to-end on a handful of rows; train years never include holdout."""
    games = []
    priors = {}
    for i, d in enumerate((4.0, 8.0, 12.0, -6.0, 10.0, 2.0, 7.0, 5.0)):
        games.append(_toy_game(f"tr{i}", 2022, 1, close=-1.6 * d, home_pts=d, away_pts=0.0))
        priors[(2022, "UGA")] = {"points": 8.0}
        priors[(2022, "CLEM")] = {"points": 0.0}
    for i, d in enumerate((5.0, 9.0, 3.0)):
        games.append(_toy_game(f"ho{i}", 2024, 1, close=-1.6 * d, home_pts=d, away_pts=0.0))
        priors[(2024, "UGA")] = {"points": 9.0}
        priors[(2024, "CLEM")] = {"points": 0.0}
    # collect_eligible reads prior from the map, not the game row.
    for g in games:
        g.pop("prior_home", None)
        g.pop("prior_away", None)
    pack = run_holdout_calibration(
        games,
        priors,
        train_years=[2022],
        holdout_years=[2024],
    )
    assert pack["fitted_scale"] > 0
    assert pack["epa_in_fair"] is False
    assert pack["used_in_spread"] is False
    assert pack["holdout"]["calibrated"]["w0_4"]["n_close"] == 3
    assert pack["train"]["calibrated"]["w0_4"]["n_close"] == 8
    # Thin holdout must not adopt.
    assert pack["adopted"] is False
    assert pack["scale"] is None
