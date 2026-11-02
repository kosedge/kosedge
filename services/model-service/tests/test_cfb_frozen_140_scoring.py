"""Frozen 1.40 scoring contract: no coeff drift, no 2025/2026, Layer B held out."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE
from src.services.cfb_season_engine.qb_feature_contract import QB_FEATURE_CONTRACT_VERSION
from src.services.cfb_warehouse.frozen_140_scoring import (
    HIGH_TOTAL_TAIL,
    VAL1_GATE,
    FrozenScoringError,
    assert_frozen_priors,
    decide,
    power_codes_for_season,
    refuse_sealed_or_confirm,
    roi_minus_110,
    summarize_scored,
)


def test_coefficients_remain_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert QB_FEATURE_CONTRACT_VERSION == "cfb-qb-feature-v1"
    assert_frozen_priors()


def test_refuses_2025_and_2026() -> None:
    try:
        refuse_sealed_or_confirm([2025])
        raise AssertionError("2025 should be sealed")
    except FrozenScoringError:
        pass
    try:
        refuse_sealed_or_confirm([2026])
        raise AssertionError("2026 should not enter the loss")
    except FrozenScoringError:
        pass
    refuse_sealed_or_confirm([2022, 2023, 2024])


def test_year_aware_power_does_not_use_2026_realignment_on_2022() -> None:
    p2022 = power_codes_for_season(2022)
    p2024 = power_codes_for_season(2024)
    assert "ORE" in p2022  # Pac-12
    assert "ORE" in p2024  # Big Ten 2024
    assert "OU" in p2022  # Big 12
    assert "OU" in p2024  # SEC 2024
    assert "SMU" not in p2022
    assert "SMU" in p2024
    assert "ORST" in p2022
    assert "ORST" not in p2024  # leftover Pac-12 is not Power 4


def test_roi_minus_110() -> None:
    assert roi_minus_110([]) is None
    # 1 win + 1 loss at -110 = (100/110 - 1) / 2
    roi = roi_minus_110([True, False])
    assert roi is not None
    assert abs(roi - ((100.0 / 110.0) - 1.0) / 2.0) < 1e-9


def test_high_tail_definition_matches_protocol() -> None:
    assert HIGH_TOTAL_TAIL == 68.0
    assert VAL1_GATE == 700


def _row(**overrides):
    base = {
        "game_id": "g",
        "season": 2024,
        "week": 3,
        "home": "ALA",
        "away": "AUB",
        "actual_margin": 7.0,
        "actual_total": 52.0,
        "close_spread_home": -6.5,
        "close_total": 50.5,
        "close_source": "odds_api_lake",
        "model_spread_home": -7.0,
        "model_total": 51.0,
        "model_home_wp": 0.62,
        "err_spread_vs_close": -0.5,
        "err_margin_vs_actual": 0.0,
        "err_total_vs_close": 0.5,
        "err_total_vs_actual": -1.0,
        "abs_disagree_spread": 0.5,
        "abs_disagree_total": 0.5,
        "ats_hit": True,
        "ou_hit": True,
        "ml_hit": True,
        "brier": 0.14,
        "favorite_home": True,
        "early_w1_2": False,
        "identity_slice": "power_vs_power",
        "high_total_tail": False,
        "established_both": True,
        "home_qb_talent": 72.0,
        "away_qb_talent": 68.0,
        "home_qb_class": "incumbent",
        "away_qb_class": "incumbent",
    }
    base.update(overrides)
    return base


def test_decide_insufficient_when_val1_thin() -> None:
    summary = summarize_scored([_row() for _ in range(10)])
    memo = decide(summary)
    assert memo["decision"] == "INSUFFICIENT EVIDENCE"


def test_decide_recalibration_on_total_inflation() -> None:
    rows = []
    for i in range(710):
        rows.append(
            _row(
                season=2022,
                game_id=f"t{i}",
                model_total=60.0,
                close_total=52.0,
                err_total_vs_close=8.0,
            )
        )
    for i in range(710):
        rows.append(
            _row(
                season=2024,
                game_id=f"v{i}",
                model_total=61.0,
                close_total=52.0,
                err_total_vs_close=9.0,
                high_total_tail=True,
            )
        )
    memo = decide(summarize_scored(rows))
    assert memo["decision"] == "RECALIBRATION JUSTIFIED"


def test_decide_validated_when_totals_near_calibrated() -> None:
    rows = []
    for i in range(710):
        rows.append(_row(season=2022, game_id=f"t{i}", err_total_vs_close=0.2))
    for i in range(710):
        rows.append(
            _row(
                season=2024,
                game_id=f"v{i}",
                model_total=52.0,
                close_total=51.8,
                err_total_vs_close=0.2,
                model_spread_home=-7.0,
                close_spread_home=-6.5,
                err_spread_vs_close=-0.5,
                abs_disagree_spread=0.5,
            )
        )
    memo = decide(summarize_scored(rows))
    assert memo["decision"] == "FROZEN 1.40 VALIDATED"
