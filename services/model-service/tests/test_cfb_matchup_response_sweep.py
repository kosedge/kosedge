"""MATCHUP_RESPONSE overlay + sweep decision: actual-primary, not Vegas-clone."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import (
    MATCHUP_RESPONSE,
    matchup_response_base,
    matchup_response_for_week,
    overlay_matchup_response,
)
from src.services.cfb_season_engine.qb_feature_contract import QB_FEATURE_CONTRACT_VERSION
from src.services.cfb_warehouse.frozen_140_scoring import assert_frozen_priors
from src.services.cfb_warehouse.matchup_response_sweep import (
    FROZEN_RESPONSE,
    coarse_grid,
    decide_coefficient,
    refine_grid,
    sanity_check_frozen_140,
)


def test_production_coefficient_stays_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert FROZEN_RESPONSE == 1.40
    assert QB_FEATURE_CONTRACT_VERSION == "cfb-qb-feature-v1"
    assert_frozen_priors()
    with overlay_matchup_response(1.10):
        assert MATCHUP_RESPONSE == 1.40
        assert abs(matchup_response_base() - 1.10) < 1e-9
        assert abs(matchup_response_for_week(10) - 1.10) < 1e-9
        assert abs(matchup_response_for_week(1) - 1.10 * 0.90) < 1e-9
    assert MATCHUP_RESPONSE == 1.40
    assert abs(matchup_response_base() - 1.40) < 1e-9
    assert abs(matchup_response_for_week(10) - 1.40) < 1e-9


def test_overlay_none_is_frozen_path() -> None:
    with overlay_matchup_response(None):
        assert abs(matchup_response_base() - 1.40) < 1e-9
    assert MATCHUP_RESPONSE == 1.40


def test_coarse_grid_is_systematic_not_a_guess() -> None:
    grid = coarse_grid()
    assert grid[0] == 0.90
    assert grid[-1] == 1.40
    assert 1.40 in grid
    assert 1.18 not in grid
    assert abs(grid[1] - grid[0] - 0.05) < 1e-9
    assert len(grid) == 11


def test_refine_grid_stays_in_authorized_band() -> None:
    grid = refine_grid(1.10)
    assert grid[0] >= 0.70
    assert grid[-1] <= 1.40
    assert 1.10 in grid
    assert abs(grid[1] - grid[0] - 0.02) < 1e-9


def _card(**overrides):
    base = {
        "n": 717,
        "mae_vs_actual": 16.65,
        "rmse_vs_actual": 20.80,
        "bias_vs_actual": 10.10,
        "medae_vs_actual": 14.50,
        "mae_vs_close": 12.20,
        "bias_vs_close": 11.34,
        "mean_abs_disagree_total": 12.20,
        "mean_model_total": 63.84,
        "mean_close_total": 52.50,
        "mean_actual_total": 53.74,
        "high_tail_n": 217,
        "high_tail_mae_vs_actual": 20.0,
        "high_tail_bias_vs_actual": 16.0,
        "high_tail_bias_vs_close": 17.79,
        "ats_n": 680,
        "ats_hit_rate": 0.487,
        "ats_roi_minus_110": -0.071,
        "ou_n": 680,
        "ou_hit_rate": 0.45,
        "ou_roi_minus_110": -0.14,
        "margin_mae_vs_actual": 13.80,
        "total_disagree_buckets": {},
    }
    base.update(overrides)
    return base


def _rec(response: float, val1=None, train=None, val0=None, phase="coarse"):
    return {
        "matchup_response": response,
        "phase": phase,
        "splits": {
            "train_0": train or {**_card(n=712), **(train or {})},
            "val_0": val0 or {**_card(n=710), **(val0 or {})},
            "val_1": val1 or _card(),
        },
    }


def _ok_sanity():
    return sanity_check_frozen_140(_card())


def test_sanity_accepts_published_543() -> None:
    memo = sanity_check_frozen_140(_card())
    assert memo["ok"] is True


def test_insufficient_when_lake_missing() -> None:
    memo = decide_coefficient([], lake_mounted=False, sanity={"ok": False})
    assert memo["decision"] == "INSUFFICIENT EVIDENCE"


def test_does_not_select_vegas_clone() -> None:
    """A candidate closer to close but worse vs actual must not win."""
    clone = _card(
        mae_vs_actual=17.20,
        rmse_vs_actual=21.50,
        bias_vs_actual=0.20,
        mae_vs_close=2.10,
        bias_vs_close=0.10,
        mean_abs_disagree_total=2.10,
        high_tail_n=8,
        high_tail_bias_vs_actual=1.0,
        high_tail_bias_vs_close=0.4,
        mean_model_total=52.7,
    )
    football = _card(
        mae_vs_actual=13.40,
        rmse_vs_actual=17.10,
        bias_vs_actual=1.80,
        medae_vs_actual=11.20,
        mae_vs_close=6.40,
        bias_vs_close=2.10,
        mean_abs_disagree_total=6.40,
        high_tail_n=40,
        high_tail_bias_vs_actual=2.5,
        high_tail_bias_vs_close=3.0,
        mean_model_total=55.5,
        ats_hit_rate=0.500,
        margin_mae_vs_actual=13.50,
    )
    frozen = _card()
    records = [
        _rec(1.00, val1=clone, train=clone, val0=clone),
        _rec(1.10, val1=football, train=football, val0=football),
        _rec(1.40, val1=frozen, train=frozen, val0=frozen),
    ]
    memo = decide_coefficient(records, lake_mounted=True, sanity=_ok_sanity())
    assert memo["decision"] == "COEFFICIENT CANDIDATE EARNED"
    assert memo["recommended"] == 1.10


def test_earned_when_actuals_and_tails_improve() -> None:
    good = _card(
        mae_vs_actual=13.10,
        rmse_vs_actual=16.80,
        bias_vs_actual=1.40,
        medae_vs_actual=10.90,
        mae_vs_close=6.10,
        bias_vs_close=1.80,
        mean_abs_disagree_total=6.10,
        high_tail_n=35,
        high_tail_bias_vs_actual=2.2,
        high_tail_bias_vs_close=2.8,
        mean_model_total=55.1,
        ats_hit_rate=0.498,
        margin_mae_vs_actual=13.40,
    )
    frozen = _card()
    records = [
        _rec(1.15, val1=good, train=good, val0=good),
        _rec(1.40, val1=frozen, train=frozen, val0=frozen),
    ]
    memo = decide_coefficient(records, lake_mounted=True, sanity=_ok_sanity())
    assert memo["decision"] == "COEFFICIENT CANDIDATE EARNED"
    assert memo["recommended"] == 1.15


def test_broader_when_140_is_best_mae() -> None:
    slightly_worse = _card(mae_vs_actual=16.90, bias_vs_actual=8.0)
    records = [
        _rec(1.20, val1=slightly_worse, train=slightly_worse, val0=slightly_worse),
        _rec(1.40, val1=_card(), train=_card(n=712), val0=_card(n=710)),
    ]
    memo = decide_coefficient(records, lake_mounted=True, sanity=_ok_sanity())
    assert memo["decision"] == "BROADER MODEL RECALIBRATION REQUIRED"
    assert memo["recommended"] is None


def test_broader_when_mae_and_bias_minima_split() -> None:
    mae_best = _card(
        mae_vs_actual=13.00,
        rmse_vs_actual=16.50,
        bias_vs_actual=7.80,
        high_tail_n=180,
        high_tail_bias_vs_actual=12.0,
        mean_abs_disagree_total=8.0,
    )
    bias_best = _card(
        mae_vs_actual=15.80,
        rmse_vs_actual=19.50,
        bias_vs_actual=0.40,
        high_tail_n=20,
        high_tail_bias_vs_actual=1.0,
        mean_abs_disagree_total=5.0,
    )
    frozen = _card()
    records = [
        _rec(0.95, val1=bias_best, train=bias_best, val0=bias_best),
        _rec(1.20, val1=mae_best, train=mae_best, val0=mae_best),
        _rec(1.40, val1=frozen, train=frozen, val0=frozen),
    ]
    memo = decide_coefficient(records, lake_mounted=True, sanity=_ok_sanity())
    assert memo["decision"] == "BROADER MODEL RECALIBRATION REQUIRED"
    assert memo["recommended"] is None
