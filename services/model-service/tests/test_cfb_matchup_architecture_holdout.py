"""Measure-only locks for matchup-architecture holdout. No coefficient writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

ROOT = Path(__file__).resolve().parents[3]
HOLDOUT = ROOT / "data/ops/cfb-matchup-architecture-holdout-20260912.json"

from src.services.cfb_season_engine.priors import (
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
    matchup_response_base,
    overlay_matchup_response,
    overlay_score_components,
    score_component_overlay,
)
from src.services.cfb_season_engine.team_features import CFB_EDGE_BOARD_PUBLIC_ENABLED
from src.services.cfb_warehouse.frozen_140_scoring import (
    LEGAL_SEASONS,
    refuse_sealed_or_confirm,
)
from src.services.cfb_warehouse.matchup_architecture_holdout import (
    E2_GRID,
    EXPERIMENTS,
    PROTOCOL_SPLITS,
    decide,
)


def test_production_constants_and_kill_switch_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    with overlay_matchup_response(1.0):
        assert abs(matchup_response_base() - 1.0) < 1e-9
        assert MATCHUP_RESPONSE == 1.40
        with overlay_score_components({"matchup_mode": "identity"}):
            assert score_component_overlay()["matchup_mode"] == "identity"
            assert MATCHUP_RESPONSE == 1.40
    assert abs(matchup_response_base() - 1.40) < 1e-9
    assert score_component_overlay() == {}


def test_splits_and_grid_are_pre_registered() -> None:
    assert PROTOCOL_SPLITS["train_0"]["seasons"] == (2022,)
    assert PROTOCOL_SPLITS["val_0"]["seasons"] == (2023,)
    assert PROTOCOL_SPLITS["val_1"]["seasons"] == (2024,)
    assert E2_GRID == (1.00, 1.15, 1.25)
    ids = [row["id"] for row in EXPERIMENTS]
    assert "baseline_140" in ids
    assert "E1_response_1.00" in ids
    assert "E2_response_1.15" in ids
    assert "E2_response_1.25" in ids
    assert "E3_raw_efficiency" in ids
    assert "E4_possessions_ppp" in ids
    assert "E5_zero_adders" in ids
    assert 1.00 in E2_GRID


def test_refuses_sealed_and_confirm_seasons() -> None:
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
    refuse_sealed_or_confirm(LEGAL_SEASONS)


def test_decision_never_ships_a_coefficient() -> None:
    empty = decide([], lake_mounted=False)
    assert empty["ship"] is False
    assert empty["decision"] == "INSUFFICIENT EVIDENCE"
    fake = decide(
        [
            {
                "id": "baseline_140",
                "splits": {
                    "train_0": {"total_bias_vs_actual": 11.9, "favorite_flips_vs_close": 200},
                    "val_0": {"total_bias_vs_actual": 12.3, "favorite_flips_vs_close": 200},
                    "val_1": {"total_bias_vs_actual": 10.1, "favorite_flips_vs_close": 180},
                },
            },
            {
                "id": "E1_response_1.00",
                "splits": {
                    "train_0": {"total_bias_vs_actual": 7.7, "favorite_flips_vs_close": 160},
                    "val_0": {"total_bias_vs_actual": 8.6, "favorite_flips_vs_close": 160},
                    "val_1": {"total_bias_vs_actual": 6.8, "favorite_flips_vs_close": 150},
                },
            },
            {
                "id": "E0_identity_matchup",
                "splits": {
                    "train_0": {"total_bias_vs_actual": -1.0},
                    "val_0": {"total_bias_vs_actual": 0.8},
                    "val_1": {"total_bias_vs_actual": 0.1},
                },
            },
        ],
        lake_mounted=True,
    )
    assert fake["ship"] is False
    assert fake["recommended_coefficient"] is None
    assert fake["decision"].endswith("DO_NOT_SHIP")


def test_holdout_artifact_does_not_ship() -> None:
    if not HOLDOUT.is_file():
        return
    payload = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    assert payload["wrote_production_coefficient"] is False
    assert payload["used_2026_for_fitting"] is False
    assert payload["opened_2025"] is False
    assert payload["kill_switch"] == "OFF"
    assert payload["decision"]["ship"] is False
    assert payload["decision"]["recommended_coefficient"] is None
    assert abs(float(payload["matchup_response_frozen"]) - 1.40) < 1e-9
    assert payload["protocol_splits"]["val_1"]["seasons"] == [2024]
