"""Unified proof layer: log → close → result → summary for NFL + CFB."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ["PROOF_LAKE_BACKEND"] = "jsonl"
os.environ["PROOF_LAKE_BACKEND"] = "jsonl"
os.environ["PROJECTION_LOG_BACKEND"] = "jsonl"

from src.services.cfb_season_engine import DEFAULT_SEASON_ENGINE_VERSION
from src.services.nfl_season_engine import DEFAULT_SEASON_ENGINE_VERSION as NFL_ENGINE_VERSION
from src.services.proof_layer.adapters import (
    payload_from_cfb_project_game,
    payload_from_nfl_game_boxes,
)
from src.services.proof_layer.core import (
    compute_spread_clv,
    log_projection,
    performance_summary,
    record_close,
    record_result,
)


def test_unified_cfb_log_close_result_summary(tmp_path) -> None:
    lake = tmp_path / "proof"
    rec = log_projection(
        payload_from_cfb_project_game(
            {
                "home_team": "ALA",
                "away_team": "UGA",
                "season": 2026,
                "week": 1,
                "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
                "spread_home": -3.5,
                "expected_total": 51.0,
                "home_win_prob": 0.58,
            }
        ),
        sport="cfb",
        lake_dir=lake,
    )
    assert rec.sport == "cfb"
    assert rec.game_key == "2026-W01-UGA@ALA"

    closed = record_close(
        rec.id,
        close_spread_home=-6.5,
        close_total=49.0,
        lake_dir=lake,
    )
    assert closed is not None
    assert closed.spread_clv == 3.0

    graded = record_result(rec.id, home_score=31, away_score=24, lake_dir=lake)
    assert graded is not None
    assert graded.grade_su == "win"

    summary = performance_summary(sport="cfb", lake_dir=lake)
    assert summary["ok"] is True
    assert summary["n_logged"] == 1
    assert summary["clv"]["avg_spread_clv"] == 3.0


def test_unified_nfl_adapter_and_summary(tmp_path) -> None:
    lake = tmp_path / "nfl_proof"
    payload = payload_from_nfl_game_boxes(
        {
            "home_team": "KC",
            "away_team": "BUF",
            "season": 2026,
            "week": 1,
            "game_id": "g1",
            "engine_version": NFL_ENGINE_VERSION,
            "n_replicates": 400,
            "game_script_summary": {
                "home_win_prob_mean": 0.62,
                "expected_total_mean": 48.5,
                "expected_home_score_mean": 26.0,
                "expected_away_score_mean": 22.5,
            },
        }
    )
    assert payload["sport"] == "nfl"
    assert payload["model_spread_home"] == -3.5  # -(26-22.5)

    rec = log_projection(payload, sport="nfl", lake_dir=lake)
    assert rec.sport == "nfl"
    assert rec.model_spread_home == -3.5

    record_close(rec.id, close_spread_home=-2.5, close_total=47.0, lake_dir=lake)
    record_result(rec.id, home_score=27, away_score=20, lake_dir=lake)

    summary = performance_summary(sport="nfl", lake_dir=lake)
    assert summary["sport_filter"] == "nfl"
    assert summary["n_logged"] == 1
    assert summary["n_with_close"] == 1
    assert summary["n_with_result"] == 1


def test_clv_only_when_close_exists() -> None:
    assert compute_spread_clv(-3.0, None) is None
    assert compute_spread_clv(-3.0, -7.0) == 4.0


def test_proof_http_endpoints(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "jsonl")
    monkeypatch.setenv("PROJECTION_LOG_BACKEND", "jsonl")
    monkeypatch.setenv("PROJECTION_LOG_DIR", str(tmp_path / "http"))
    import src.services.proof_layer.core as core

    monkeypatch.setattr(core, "LAKE_DIR", tmp_path / "http")

    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)

    logged = client.post(
        "/proof/projections",
        json={
            "sport": "cfb",
            "home_team": "TEX",
            "away_team": "OU",
            "season": 2026,
            "week": 2,
            "spread_home": -7.0,
            "expected_total": 55.0,
            "home_win_prob": 0.68,
        },
    )
    assert logged.status_code == 200
    proj_id = logged.json()["projection"]["id"]

    close = client.post(
        f"/proof/projections/{proj_id}/close",
        json={"close_spread_home": -4.0, "close_total": 53.5},
    )
    assert close.status_code == 200
    assert close.json()["projection"]["spread_clv"] == -3.0

    result = client.post(
        f"/proof/projections/{proj_id}/result",
        json={"home_score": 34, "away_score": 27},
    )
    assert result.status_code == 200

    perf = client.get("/proof/performance?sport=cfb")
    assert perf.status_code == 200
    assert perf.json()["n_logged"] >= 1


def test_nfl_game_boxes_log_projection_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "jsonl")
    monkeypatch.setenv("PROJECTION_LOG_BACKEND", "jsonl")
    monkeypatch.setenv("PROJECTION_LOG_DIR", str(tmp_path / "nfl_http"))
    import src.services.proof_layer.core as core

    monkeypatch.setattr(core, "LAKE_DIR", tmp_path / "nfl_http")

    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    resp = client.get(
        "/nfl/season-engine/game-boxes",
        params={
            "home_team": "KC",
            "away_team": "BUF",
            "week": 1,
            "demo": True,
            "n_replicates": 50,
            "log_projection": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("projection_logged") is True
    assert data.get("projection_log_id")

    perf = client.get("/proof/performance?sport=nfl")
    assert perf.json()["n_logged"] >= 1
