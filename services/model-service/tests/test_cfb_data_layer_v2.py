"""Locks for CFB Data Layer v2. No coefficient writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import LEAGUE_TEAM_PPG, MATCHUP_RESPONSE
from src.services.cfb_season_engine.team_features import CFB_EDGE_BOARD_PUBLIC_ENABLED
from src.services.cfb_warehouse.data_layer_v2 import (
    COMPOSITE_MEMBERS,
    FEATURE_SPECS,
    HIGH_ENV_THRESHOLD,
    LAYER_B_GAP,
    LEGAL_PBP_SEASONS,
    STABLE_AUC,
    classify_drive,
    decide,
    pbp_path,
    refuse_sealed_pbp,
    snapshot_team,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    FrozenScoringError,
    refuse_sealed_or_confirm,
)
from src.services.cfb_warehouse.matchup_architecture_holdout import PROTOCOL_SPLITS

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data/ops/cfb-data-layer-v2-20260912.json"


def test_production_and_target_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    assert HIGH_ENV_THRESHOLD == 68.0
    assert STABLE_AUC == 0.55
    assert PROTOCOL_SPLITS["val_1"]["seasons"] == (2024,)
    assert LEGAL_PBP_SEASONS == (2021, 2022, 2023, 2024)


def test_features_are_predeclared_and_have_no_capture_target() -> None:
    ids = [s["id"] for s in FEATURE_SPECS]
    assert ids[0] == "curr_sum_off_epa"
    assert "curr_sum_pace_plays" in ids
    assert "curr_sum_explosive_allowed" in ids
    assert "curr_sum_finish" in ids
    assert "curr_sum_havoc_created" in ids
    assert "curr_mean_game_total" in ids
    assert "layer_b_returning" in ids
    assert "close_total" in ids
    close = next(s for s in FEATURE_SPECS if s["id"] == "close_total")
    assert close["role"] == "diagnostic"
    layer_b = next(s for s in FEATURE_SPECS if s["id"] == "layer_b_returning")
    assert layer_b["role"] == "source_gap"
    assert LAYER_B_GAP["status"] == "SOURCE_GAP"
    assert "close_total" not in COMPOSITE_MEMBERS
    assert "curr_mean_game_total" in COMPOSITE_MEMBERS
    assert "prior_mean_game_total" in COMPOSITE_MEMBERS


def test_refuses_2025_and_2026_pbp_without_opening_files() -> None:
    try:
        refuse_sealed_pbp([2025])
        raise AssertionError("2025 PBP must stay sealed")
    except FrozenScoringError as exc:
        assert "2025" in str(exc)
    try:
        pbp_path(2025)
        raise AssertionError("pbp_path(2025) must refuse")
    except FrozenScoringError as exc:
        assert "2025" in str(exc)
    try:
        refuse_sealed_pbp([2026])
        raise AssertionError("2026 PBP must stay out of the loss")
    except FrozenScoringError as exc:
        assert "2026" in str(exc) or "2025" in str(exc)
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
    refuse_sealed_pbp([2021])  # prior-year PBP is legal
    try:
        refuse_sealed_or_confirm([2021])
        raise AssertionError("2021 is not a scoring season")
    except FrozenScoringError:
        pass


def test_cold_start_is_missing_not_zero() -> None:
    row = snapshot_team(
        [],
        season=2022,
        week=1,
        team="ALA",
        adj={"ALA": {"off_epa_adj": 0.12, "def_epa_adj": -0.08}},
        source="current_season",
    )
    assert row["available"] is False
    assert row["availability"] == "MISSING_COLD_START"
    assert row["n_games"] == 0
    assert row["max_week_included"] == 0
    for key in (
        "off_epa_adj",
        "def_epa_adj",
        "off_epa_raw",
        "explosive_created",
        "havoc_created",
        "finish_rate",
        "ppp",
        "pace_plays",
    ):
        assert row[key] is None


def test_thin_sample_is_missing_not_zero() -> None:
    games = [
        {
            "season": 2022,
            "week": 1,
            "team_id": "ALA",
            "opponent_id": "UTAH",
            "n_plays": 70,
            "n_plays_weighted": 70.0,
            "off_epa_raw": 0.20,
            "off_success_raw": 0.45,
            "off_explosive_rate": 0.08,
            "havoc_allowed": 0.12,
            "finish_rate": 0.40,
            "ppp": 2.1,
        }
    ]
    row = snapshot_team(
        games,
        season=2022,
        week=2,
        team="ALA",
        adj={"ALA": {"off_epa_adj": 0.20, "def_epa_adj": 0.01}},
        source="current_season",
    )
    assert row["available"] is False
    assert row["availability"] == "MISSING_THIN_SAMPLE"
    assert row["n_games"] == 1
    assert row["off_epa_adj"] is None
    assert row["pace_plays"] is None


def test_present_snapshot_excludes_target_and_future_weeks() -> None:
    games = [
        {
            "season": 2022,
            "week": week,
            "team_id": "ALA",
            "opponent_id": "UTAH",
            "n_plays": 60 + week,
            "n_plays_weighted": 60.0,
            "off_epa_raw": 0.10,
            "off_success_raw": 0.40,
            "off_explosive_rate": 0.07,
            "havoc_allowed": 0.10,
            "finish_rate": 0.35,
            "ppp": 1.8,
        }
        for week in (1, 2, 3, 8)
    ]
    row = snapshot_team(
        games,
        season=2022,
        week=4,
        team="ALA",
        adj={"ALA": {"off_epa_adj": 0.11, "def_epa_adj": 0.02}},
        source="current_season",
    )
    assert row["available"] is True
    assert row["n_games"] == 3
    assert row["max_week_included"] == 3
    assert row["off_epa_adj"] == 0.11
    assert row["pace_plays"] == (61 + 62 + 63) / 3


def test_drive_result_decode_is_not_a_proxy_fill() -> None:
    assert classify_drive("TD") == (6.0, True)
    assert classify_drive("FG") == (3.0, True)
    assert classify_drive("PUNT") == (0.0, False)
    assert classify_drive("INT TD") == (0.0, False)
    assert classify_drive("Not provided") is None
    assert classify_drive(None) is None


def test_decision_never_ships() -> None:
    empty = decide({})
    assert empty["ship"] is False
    assert empty["winner"] is None
    assert empty["play"] is False
    assert empty["decision"] == "DATA_LAYER_V2_BUILT_SIGNAL_NOT_STABLE"


def test_artifact_if_present_does_not_ship() -> None:
    if not ART.is_file():
        return
    payload = json.loads(ART.read_text(encoding="utf-8"))
    assert payload["wrote_production_coefficient"] is False
    assert payload["used_2026_for_fitting"] is False
    assert payload["opened_2025"] is False
    assert payload["scoring_equation_frozen"] is True
    assert payload["do_not_tune"] is True
    assert payload["play"] is False
    assert payload["kill_switch"] == "OFF"
    assert payload["decision"]["ship"] is False
    assert payload["decision"]["winner"] is None
    assert payload["target"]["threshold"] == 68.0
    assert payload["target"]["capture_target"] is None
    assert payload["stability_gate"]["capture_target"] is None
    assert abs(float(payload["matchup_response_frozen"]) - 1.40) < 1e-9
    leak = payload.get("leakage") or {}
    assert leak.get("opened_2025") is False
    assert leak.get("prior_season_always_ym1") is True
    assert leak.get("close_in_v2_features") is False
    assert (payload.get("layer_b") or {}).get("status") == "SOURCE_GAP"
    paths = [
        str((payload.get("source_meta") or {}).get(season, {}).get("path") or "")
        for season in ("2021", "2022", "2023", "2024", "2025")
    ]
    assert not any("2025" in p or "2026" in p for p in paths)
