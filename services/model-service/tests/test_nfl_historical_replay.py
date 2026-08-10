"""Phase 3 historical replay — no-look-ahead guards + scorecard math."""

from __future__ import annotations

import math

import pytest

from src.services.nfl_season_engine.historical_replay import (
    REPLAY_PROTOCOL_VERSION,
    assert_no_lookahead_inputs,
    bias,
    mae,
    pool_scorecards,
    score_vector,
    spearman_rank_corr,
    verdict_from_pooled,
    SeasonScorecard,
)


def test_protocol_version_stable() -> None:
    assert REPLAY_PROTOCOL_VERSION.startswith("nfl-historical-replay-v1")


def test_mae_bias_scorecard_math() -> None:
    pred = {"A": 10.0, "B": 8.0, "C": 6.0}
    actual = {"A": 12.0, "B": 7.0, "C": 6.0}
    # errors: -2, +1, 0
    assert mae([-2.0, 1.0, 0.0]) == pytest.approx(1.0)
    assert bias([-2.0, 1.0, 0.0]) == pytest.approx(-1.0 / 3.0)
    scored = score_vector(pred, actual)
    assert scored["n"] == 3
    assert scored["mae"] == pytest.approx(1.0)
    assert scored["bias"] == pytest.approx((-2.0 + 1.0 + 0.0) / 3.0)


def test_spearman_perfect_and_inverse() -> None:
    x = [1.0, 2.0, 3.0, 4.0]
    y = [10.0, 20.0, 30.0, 40.0]
    assert spearman_rank_corr(x, y) == pytest.approx(1.0)
    assert spearman_rank_corr(x, list(reversed(y))) == pytest.approx(-1.0)


def test_no_lookahead_guards_reject_current_season_strength() -> None:
    with pytest.raises(AssertionError):
        assert_no_lookahead_inputs(
            season=2023,
            strength_meta={
                "prior_season": 2023,  # wrong — must be Y-1
                "forbidden": "season_Y_rolling_features",
            },
            depth_meta={"season": 2023, "week": 1, "look_ahead": False},
        )


def test_no_lookahead_guards_reject_midseason_depth() -> None:
    with pytest.raises(AssertionError):
        assert_no_lookahead_inputs(
            season=2022,
            strength_meta={
                "prior_season": 2021,
                "forbidden": "season_Y_rolling_features",
            },
            depth_meta={"season": 2022, "week": 10, "look_ahead": False},
        )


def test_no_lookahead_guards_accept_valid_preseason() -> None:
    assert_no_lookahead_inputs(
        season=2024,
        strength_meta={
            "prior_season": 2023,
            "forbidden": "season_Y_rolling_features",
        },
        depth_meta={"season": 2024, "week": 1, "look_ahead": False},
    )


def test_verdict_reports_loss_to_prior_year() -> None:
    cards = [
        SeasonScorecard(
            season=2022,
            engine_version="test",
            snapshot_id="snap",
            n_sims=10,
            model_team={
                "wins": {"n": 32, "mae": 3.5, "bias": 0.1, "rank_corr": 0.2}
            },
            baselines={
                "prior_year_regression": {
                    "wins": {"n": 32, "mae": 2.0, "bias": 0.0, "rank_corr": 0.4}
                },
                "epa_power": {
                    "wins": {"n": 32, "mae": 2.5, "bias": 0.0, "rank_corr": 0.3}
                },
            },
        )
    ]
    pooled = pool_scorecards(cards)
    verdict = verdict_from_pooled(pooled)
    assert verdict["phase4_infrastructure_unblocked"] is True
    assert verdict["phase4_model_claim_unblocked"] is False
    assert any("prior_year_regression" in x for x in verdict["not_earned"])
    assert math.isfinite(float(verdict["model_wins_mae"]))


def test_player_match_key_normalizes_pbp_and_full_names() -> None:
    from src.services.nfl_season_engine.historical_replay import _player_match_key

    assert _player_match_key("Josh Allen") == _player_match_key("J.Allen")
    assert _player_match_key("A.J. Brown") == _player_match_key("AJ Brown")
