"""Locks for CFBD research ingest. No coefficient writes. No secret leakage."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import LEAGUE_TEAM_PPG, MATCHUP_RESPONSE
from src.services.cfb_season_engine.team_features import CFB_EDGE_BOARD_PUBLIC_ENABLED
from src.services.cfb_warehouse.cfbd_client import (
    redact,
    refuse_sealed_params,
    refuse_sealed_year,
)
from src.services.cfb_warehouse.cfbd_ingest import (
    FEATURE_MAP,
    RESEARCH_CALL_BUDGET,
    _audit_decision,
    assert_point_in_time_safe,
    flatten_advanced_team,
    through_week_for_game,
)
from src.services.cfb_warehouse.frozen_140_scoring import FrozenScoringError

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data/ops/cfb-cfbd-acquisition-20260912.json"


def test_production_frozen() -> None:
    assert MATCHUP_RESPONSE == 1.40
    assert abs(LEAGUE_TEAM_PPG - 25.9) < 1e-9
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
    assert RESEARCH_CALL_BUDGET["first_pass_no_pbp_no_core"] < 100
    assert RESEARCH_CALL_BUDGET["monthly_free_tier"] == 1000


def test_feature_map_is_predeclared() -> None:
    needs = [row["need"] for row in FEATURE_MAP]
    assert "true_pace_plays" in needs
    assert "explosiveness" in needs
    assert "returning_production" in needs
    assert "core_opponent_adjusted" in needs
    classes = {row["need"]: row["class"] for row in FEATURE_MAP}
    assert classes["explosiveness"] == "DIRECT"
    assert classes["weather"] == "UNAVAILABLE"
    assert classes["sp_plus"] == "EXTERNAL_RATING"
    assert classes["core_opponent_adjusted"] == "POINT_IN_TIME_RISK"
    assert classes["betting_lines"] == "POINT_IN_TIME_RISK"
    assert classes["stats_player_success"] == "UNAVAILABLE"


def test_refuses_2025_and_2026() -> None:
    try:
        refuse_sealed_year(2025)
        raise AssertionError("2025 must stay sealed")
    except FrozenScoringError as exc:
        assert "2025" in str(exc)
    try:
        refuse_sealed_params({"year": 2026})
        raise AssertionError("2026 must stay out of the loss")
    except FrozenScoringError:
        pass


def test_week_w_uses_only_end_week_w_minus_1() -> None:
    assert through_week_for_game(1) is None
    assert through_week_for_game(8) == 7
    assert_point_in_time_safe(game_week=8, through_week=7)
    try:
        assert_point_in_time_safe(game_week=8, through_week=8)
        raise AssertionError("through_week >= game week must fail")
    except FrozenScoringError:
        pass


def test_missing_advanced_fields_stay_none() -> None:
    row = flatten_advanced_team(
        {"team": "Alabama", "offense": {}, "defense": {}},
        year=2022,
        through_week=3,
    )
    assert row["off_ppa"] is None
    assert row["def_explosiveness"] is None
    assert row["off_ppp"] is None
    assert row["is_point_in_time_safe"] is True
    assert 50 not in row.values()


def test_redact_never_echoes_a_supplied_secret(monkeypatch) -> None:
    monkeypatch.setenv("CFBD_API_KEY", "super-secret-test-key")
    assert "super-secret-test-key" not in redact("Authorization: Bearer super-secret-test-key")
    assert "[REDACTED]" in redact("super-secret-test-key")


def test_auth_failure_does_not_ship() -> None:
    gate = _audit_decision(True, [{"status": 401}, {"status": 401}])
    assert gate["ship"] is False
    assert gate["play"] is False
    assert gate["decision"] == "CFBD_AUTH_FAILED_DO_NOT_INGEST"


def test_artifact_if_present_does_not_ship_or_leak() -> None:
    if not ART.is_file():
        return
    text = ART.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["wrote_production_coefficient"] is False
    assert payload["opened_2025"] is False
    assert payload["bulk_ingest"] is False
    assert payload["high_env_rerun"] is False
    assert payload["play"] is False
    assert payload["decision"]["ship"] is False
    assert payload["decision"]["winner"] is None
    assert "Bearer " not in text
    assert "HDWo" not in text
    assert abs(float(payload["matchup_response_frozen"]) - 1.40) < 1e-9
