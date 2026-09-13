"""Locks for raw O/D specification. No coefficient writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import (
    MATCHUP_RESPONSE,
    overlay_score_components,
    score_component_overlay,
)
from src.services.cfb_season_engine.team_features import CFB_EDGE_BOARD_PUBLIC_ENABLED
from src.services.cfb_warehouse.frozen_140_scoring import refuse_sealed_or_confirm
from src.services.cfb_warehouse.matchup_architecture_holdout import PROTOCOL_SPLITS
from src.services.cfb_warehouse.raw_od_interaction import (
    CANDIDATES,
    RANGE_DROP,
    decide,
)

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data/ops/cfb-raw-od-interaction-20260912.json"


def test_production_and_kill_switch_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    with overlay_score_components({"matchup_mode": "raw_diff"}):
        assert score_component_overlay()["matchup_mode"] == "raw_diff"
        assert MATCHUP_RESPONSE == 1.40
    assert score_component_overlay() == {}


def test_candidates_are_predeclared() -> None:
    ids = [c["id"] for c in CANDIDATES]
    assert ids[0] == "E3_raw_efficiency_r1"
    assert "C1_e3_no_leak" in ids
    assert "C2_raw_additive" in ids
    assert "C3_raw_diff" in ids
    assert "C4_raw_sat" in ids
    assert RANGE_DROP == 8.0
    assert PROTOCOL_SPLITS["val_1"]["seasons"] == (2024,)


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
    empty = decide([])
    assert empty["ship"] is False
    assert empty["winner"] is None


def test_artifact_if_present_does_not_ship() -> None:
    if not ART.is_file():
        return
    payload = json.loads(ART.read_text(encoding="utf-8"))
    assert payload["wrote_production_coefficient"] is False
    assert payload["used_2026_for_fitting"] is False
    assert payload["opened_2025"] is False
    assert payload["kill_switch"] == "OFF"
    assert payload["decision"]["ship"] is False
    assert payload["decision"]["winner"] is None
    assert abs(float(payload["matchup_response_frozen"]) - 1.40) < 1e-9
