from __future__ import annotations

from data_platform_nfl.preseason_hydration import (
    ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES,
    blend_usage_rates,
    compute_rolling_blend_weight,
)


def test_rolling_blend_weight_ramps_linearly_to_full_weight() -> None:
    assert compute_rolling_blend_weight(0.0) == 0.0
    assert compute_rolling_blend_weight(ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES / 2.0) == 0.5
    assert compute_rolling_blend_weight(ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES) == 1.0


def test_rolling_blend_weight_never_exceeds_one_past_full_weight_games() -> None:
    # A player with 10 real games in hand (well past the shrinkage window)
    # should get FULL real-data weight, not something >1.0 that would let
    # the real signal overshoot when blended.
    assert compute_rolling_blend_weight(10.0) == 1.0
    assert compute_rolling_blend_weight(100.0) == 1.0


def test_blend_usage_rates_at_zero_weight_returns_existing_prior_unchanged() -> None:
    real = {"targets": 8.0, "rush_attempts": 0.0}
    existing = {"targets": 2.0, "rush_attempts": 1.0}
    blended = blend_usage_rates(real, existing, weight_real=0.0)
    assert blended["targets"] == 2.0
    assert blended["rush_attempts"] == 1.0


def test_blend_usage_rates_at_full_weight_returns_real_data_unchanged() -> None:
    real = {"targets": 8.0, "rush_attempts": 0.0}
    existing = {"targets": 2.0, "rush_attempts": 1.0}
    blended = blend_usage_rates(real, existing, weight_real=1.0)
    assert blended["targets"] == 8.0
    assert blended["rush_attempts"] == 0.0


def test_blend_usage_rates_midweight_is_a_true_average() -> None:
    real = {"targets": 10.0}
    existing = {"targets": 4.0}
    blended = blend_usage_rates(real, existing, weight_real=0.5)
    assert blended["targets"] == 7.0


def test_blend_usage_rates_reflects_a_breakout_rookie_scenario() -> None:
    # A rookie WR seeded at a modest draft-tier baseline (3 targets/game) who
    # has actually been getting 9 targets/game across his first 2 real
    # weeks should see his remaining-week projection meaningfully rise
    # toward, but not all the way to, his real early-season rate (2 games
    # in hand is still below the 4-game full-weight threshold).
    weight = compute_rolling_blend_weight(2.0)
    blended = blend_usage_rates({"targets": 9.0}, {"targets": 3.0}, weight_real=weight)
    assert 3.0 < blended["targets"] < 9.0
    assert weight == 0.5
    assert blended["targets"] == 6.0
