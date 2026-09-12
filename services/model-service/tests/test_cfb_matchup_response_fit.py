"""MATCHUP_RESPONSE fit contract: isolate the exponent, keep production at 1.40."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE
from src.services.cfb_season_engine.qb_feature_contract import QB_FEATURE_CONTRACT_VERSION
from src.services.cfb_warehouse.frozen_140_scoring import refuse_sealed_or_confirm
from src.services.cfb_warehouse.matchup_response_fit import (
    COARSE_GRID,
    PRODUCTION_MATCHUP_RESPONSE,
    FitError,
    decide_fit,
    primary_loss,
    refine_grid,
    select_from_losses,
    slim_split,
    temporary_matchup_response,
)


def test_production_coefficient_untouched() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert PRODUCTION_MATCHUP_RESPONSE == 1.40
    assert QB_FEATURE_CONTRACT_VERSION == "cfb-qb-feature-v1"


def test_grid_is_systematic_and_118_is_unprivileged() -> None:
    assert 1.40 in COARSE_GRID
    assert 1.18 in COARSE_GRID
    assert COARSE_GRID.count(1.18) == 1
    # 1.18 is just another node — neighbors exist on both sides.
    assert 1.15 in COARSE_GRID
    assert 1.20 in COARSE_GRID
    steps = [round(COARSE_GRID[i + 1] - COARSE_GRID[i], 2) for i in range(len(COARSE_GRID) - 1)]
    assert all(0.02 <= s <= 0.05 for s in steps)


def test_temporary_override_restores_production() -> None:
    assert P.MATCHUP_RESPONSE == 1.40
    with temporary_matchup_response(1.05):
        assert P.MATCHUP_RESPONSE == 1.05
        assert P.matchup_response_for_week(5) == 1.05
    assert P.MATCHUP_RESPONSE == 1.40
    assert MATCHUP_RESPONSE == 1.40


def test_temporary_override_restores_after_error() -> None:
    try:
        with temporary_matchup_response(0.90):
            assert P.MATCHUP_RESPONSE == 0.90
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert P.MATCHUP_RESPONSE == 1.40


def test_refuses_2025_and_2026() -> None:
    try:
        refuse_sealed_or_confirm([2025])
        raise AssertionError("2025 should stay sealed")
    except Exception:
        pass
    try:
        refuse_sealed_or_confirm([2026])
        raise AssertionError("2026 must not enter the loss")
    except Exception:
        pass


def _split(**overrides):
    base = {
        "n": 710,
        "primary_loss": 20.0,
        "total_vs_actual_mae": 16.0,
        "total_vs_actual_bias": 10.0,
        "total_vs_close_mae": 12.0,
        "total_vs_close_bias": 11.0,
        "margin_vs_actual_mae": 14.8,
        "mean_abs_model_spread": 7.2,
        "mean_abs_close_spread": 10.6,
        "slices": {
            "frozen140_high_tail": {
                "n": 217,
                "total_vs_actual_bias": 16.0,
            }
        },
    }
    base.update(overrides)
    return base


def _summary(val1, train1=None, val0=None, train0=None):
    return {
        "splits": {
            "train_0": train0 or _split(n=712, primary_loss=18.0),
            "val_0": val0 or _split(n=710, primary_loss=19.0),
            "train_1": train1 or _split(n=1422, primary_loss=18.5),
            "val_1": val1,
        }
    }


def test_selects_on_train1_not_intuition() -> None:
    cands = {
        1.18: _summary(_split(), train1=_split(primary_loss=17.0)),
        1.05: _summary(_split(), train1=_split(primary_loss=12.0)),
        1.40: _summary(_split(), train1=_split(primary_loss=20.0)),
    }
    assert select_from_losses(cands) == 1.05


def test_decide_earned_when_actuals_and_stability_clear() -> None:
    baseline = _summary(_split())
    good = _split(
        primary_loss=10.0,
        total_vs_actual_mae=13.0,
        total_vs_actual_bias=3.0,
        total_vs_close_mae=10.0,
        margin_vs_actual_mae=14.5,
        slices={"frozen140_high_tail": {"n": 217, "total_vs_actual_bias": 6.0}},
    )
    cands = {
        1.05: _summary(good, train1=_split(primary_loss=10.0), val0=_split(primary_loss=10.5)),
        1.40: baseline,
        1.00: _summary(good, train1=_split(primary_loss=10.4)),
        1.10: _summary(good, train1=_split(primary_loss=10.6)),
    }
    memo = decide_fit(baseline=baseline, candidates=cands, selected=1.05)
    assert memo["decision"] == "COEFFICIENT CANDIDATE EARNED"


def test_decide_broader_when_spreads_collapse() -> None:
    baseline = _summary(_split())
    collapsed = _split(
        primary_loss=10.0,
        total_vs_actual_mae=13.0,
        total_vs_actual_bias=3.0,
        margin_vs_actual_mae=14.5,
        mean_abs_model_spread=2.0,
        mean_abs_close_spread=10.6,
        slices={"frozen140_high_tail": {"n": 217, "total_vs_actual_bias": 6.0}},
    )
    cands = {0.80: _summary(collapsed, train1=_split(primary_loss=10.0))}
    memo = decide_fit(baseline=baseline, candidates=cands, selected=0.80)
    assert memo["decision"] == "BROADER MODEL RECALIBRATION REQUIRED"


def test_decide_broader_when_actuals_do_not_clear() -> None:
    baseline = _summary(_split())
    weak = _split(
        primary_loss=19.0,
        total_vs_actual_mae=15.8,
        total_vs_actual_bias=9.2,
        slices={"frozen140_high_tail": {"n": 217, "total_vs_actual_bias": 14.0}},
    )
    cands = {
        1.18: _summary(weak, train1=_split(primary_loss=19.0)),
        1.40: _summary(_split(primary_loss=20.5), train1=_split(primary_loss=20.5)),
    }
    memo = decide_fit(baseline=baseline, candidates=cands, selected=1.18)
    assert memo["decision"] == "BROADER MODEL RECALIBRATION REQUIRED"


def test_decide_insufficient_when_n_fails() -> None:
    baseline = _summary(_split(n=20), train0=_split(n=20))
    memo = decide_fit(baseline=baseline, candidates={1.40: baseline}, selected=1.40)
    assert memo["decision"] == "INSUFFICIENT EVIDENCE"


def test_primary_loss_uses_actuals() -> None:
    loss = primary_loss(
        {
            "total_vs_actual_mae": 10.0,
            "total_vs_actual_bias": 4.0,
            "slices": {"frozen140_high_tail": {"total_vs_actual_bias": 8.0}},
        }
    )
    assert loss == 10.0 + 0.25 * 4.0 + 0.50 * 8.0


def test_refine_skips_coarse_nodes() -> None:
    extra = refine_grid(1.05)
    assert 1.05 not in extra
    assert 1.02 in extra
    assert 1.00 not in extra


def test_slim_split_keeps_required_diagnostics() -> None:
    slim = slim_split(_split())
    assert slim["n"] == 710
    assert "total_vs_actual_mae" in slim
    assert "total_vs_close_bias" in slim
    assert "frozen140_high_tail" in slim


def test_cannot_start_if_production_drifted() -> None:
    prior = P.MATCHUP_RESPONSE
    P.MATCHUP_RESPONSE = 1.18
    try:
        try:
            with temporary_matchup_response(1.00):
                pass
            raise AssertionError("should refuse drifted production")
        except FitError:
            pass
    finally:
        P.MATCHUP_RESPONSE = prior
    assert P.MATCHUP_RESPONSE == 1.40
