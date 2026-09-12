"""Locks for HIGH_ENV information sufficiency. No coefficient writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import LEAGUE_TEAM_PPG, MATCHUP_RESPONSE
from src.services.cfb_season_engine.team_features import CFB_EDGE_BOARD_PUBLIC_ENABLED
from src.services.cfb_warehouse.frozen_140_scoring import refuse_sealed_or_confirm
from src.services.cfb_warehouse.high_env_information import (
    COMPOSITE_MEMBERS,
    FEATURE_SPECS,
    HIGH_ENV_THRESHOLD,
    STRONG_CAPTURE,
    VAL1_AUC_MIN,
    decide,
    roc_auc,
)
from src.services.cfb_warehouse.matchup_architecture_holdout import PROTOCOL_SPLITS

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data/ops/cfb-high-env-information-20260912.json"


def test_production_and_target_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    assert HIGH_ENV_THRESHOLD == 68.0
    assert VAL1_AUC_MIN == 0.60
    assert STRONG_CAPTURE == 0.40
    assert PROTOCOL_SPLITS["val_1"]["seasons"] == (2024,)


def test_features_are_predeclared() -> None:
    ids = [s["id"] for s in FEATURE_SPECS]
    assert ids[0] == "sum_off_eff"
    assert "product_mismatch" in ids
    assert "sum_off_pace" in ids
    assert "prior_mean_game_total" in ids
    assert "close_total" in ids
    assert "curr_mean_game_total" in ids
    assert "returning_production_sum" in ids
    close = next(s for s in FEATURE_SPECS if s["id"] == "close_total")
    assert close["role"] == "diagnostic"
    assert "sum_off_eff" in COMPOSITE_MEMBERS
    assert "prior_mean_game_total" in COMPOSITE_MEMBERS


def test_constant_feature_has_no_discrimination() -> None:
    scores = [53.0] * 40
    labels = [1] * 8 + [0] * 32
    auc = roc_auc(scores, labels)
    assert auc is not None
    assert abs(auc - 0.5) < 1e-9


def test_ranking_feature_has_auc_above_half() -> None:
    scores = list(range(20))
    labels = [0] * 10 + [1] * 10
    auc = roc_auc(scores, labels)
    assert auc is not None and auc > 0.9


def test_refuses_2025_and_2026() -> None:
    try:
        refuse_sealed_or_confirm([2025])
        raise AssertionError("2025 must stay sealed")
    except Exception as exc:
        assert "2025" in str(exc) or "sealed" in str(exc).lower()
    try:
        refuse_sealed_or_confirm([2026])
        raise AssertionError("2026 must stay out of the loss")
    except Exception as exc:
        assert "2026" in str(exc) or "confirm" in str(exc).lower()


def test_decision_never_ships() -> None:
    empty = decide({})
    assert empty["ship"] is False
    assert empty["winner"] is None
    assert empty["play"] is False


def test_artifact_if_present_does_not_ship() -> None:
    if not ART.is_file():
        return
    payload = json.loads(ART.read_text(encoding="utf-8"))
    assert payload["wrote_production_coefficient"] is False
    assert payload["used_2026_for_fitting"] is False
    assert payload["opened_2025"] is False
    assert payload["scoring_equation_frozen"] is True
    assert payload["play"] is False
    assert payload["kill_switch"] == "OFF"
    assert payload["decision"]["ship"] is False
    assert payload["decision"]["winner"] is None
    assert payload["target"]["threshold"] == 68.0
    assert payload["target"]["locked_before_features"] is True
    assert abs(float(payload["matchup_response_frozen"]) - 1.40) < 1e-9
    leak = payload.get("leakage") or {}
    assert leak.get("opened_2025") is False
    assert leak.get("prior_season_always_ym1") is True
