"""CFB performance tracking: log → close → result → summary."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ["CFB_PROJECTION_LOG_BACKEND"] = "jsonl"

from src.services.cfb_season_engine import DEFAULT_SEASON_ENGINE_VERSION
from src.services.cfb_season_engine.performance_tracking import (
    compute_spread_clv,
    compute_total_clv,
    grade_projection,
    log_projection,
    performance_summary,
    record_close,
    record_result,
)


def test_spread_clv_sign_convention() -> None:
    # Model −3, close −7 → +4 (beat close on home-side price)
    assert compute_spread_clv(-3.0, -7.0) == 4.0
    # Model more home-favoring than close → negative CLV
    assert compute_spread_clv(-7.0, -3.0) == -4.0
    assert compute_spread_clv(None, -3.0) is None
    assert compute_total_clv(52.0, 49.5) == 2.5


def test_grade_ats_ou_su() -> None:
    # Model home −7, close −3, home wins 28-17 (margin +11) → home covers −3
    # Model liked home more than close (edge = close - model = 4) → ATS win
    grades = grade_projection(
        {
            "model_spread_home": -7.0,
            "close_spread_home": -3.0,
            "model_total": 52.0,
            "close_total": 48.0,
            "home_win_prob": 0.72,
            "home_score": 28,
            "away_score": 17,
        }
    )
    assert grades["grade_ats"] == "win"
    # actual total 45, close 48 → under; model 52 > close → model over → loss
    assert grades["grade_ou"] == "loss"
    assert grades["grade_su"] == "win"


def test_log_close_result_summary(tmp_path) -> None:
    lake = tmp_path / "logs"
    rec = log_projection(
        {
            "home_team": "ALA",
            "away_team": "UGA",
            "season": 2026,
            "week": 1,
            "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
            "spread_home": -3.5,
            "expected_total": 51.0,
            "home_win_prob": 0.58,
            "away_win_prob": 0.42,
            "expected_home_score": 27.0,
            "expected_away_score": 24.0,
            "drivers": {"summary": {"home_sp_plus": 20.0}},
        },
        lake_dir=lake,
    )
    assert rec.id
    assert rec.game_key == "2026-W01-UGA@ALA"
    assert rec.engine_version == DEFAULT_SEASON_ENGINE_VERSION
    assert (lake / "projections.jsonl").exists()

    closed = record_close(
        rec.id,
        close_spread_home=-6.5,
        close_total=49.0,
        source="manual_test",
        lake_dir=lake,
    )
    assert closed is not None
    assert closed.spread_clv == 3.0  # -3.5 - (-6.5)
    assert closed.total_clv == 2.0

    graded = record_result(
        rec.id, home_score=31, away_score=24, source="manual_test", lake_dir=lake
    )
    assert graded is not None
    assert graded.home_score == 31
    assert graded.grade_su == "win"
    assert graded.grade_ats in {"win", "loss", "push"}
    assert graded.grade_ou in {"win", "loss", "push"}

    summary = performance_summary(lake_dir=lake, limit=50)
    assert summary["ok"] is True
    assert summary["n_logged"] == 1
    assert summary["n_with_close"] == 1
    assert summary["n_with_result"] == 1
    assert summary["clv"]["avg_spread_clv"] == 3.0
    assert summary["current_engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert summary["recent"][0]["id"] == rec.id


def test_performance_http_endpoints(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CFB_PROJECTION_LOG_BACKEND", "jsonl")
    monkeypatch.setenv("CFB_PROJECTION_LOG_DIR", str(tmp_path / "http_logs"))
    import src.services.cfb_season_engine.performance_tracking as pt

    monkeypatch.setattr(pt, "LAKE_DIR", tmp_path / "http_logs")
    monkeypatch.setattr(pt, "BACKEND", "jsonl")

    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)

    logged = client.post(
        "/cfb/season-engine/projections/log",
        json={
            "home_team": "TEX",
            "away_team": "OU",
            "season": 2026,
            "week": 2,
            "spread_home": -7.0,
            "expected_total": 55.0,
            "home_win_prob": 0.68,
            "away_win_prob": 0.32,
            "expected_home_score": 31.0,
            "expected_away_score": 24.0,
            "drivers": {"matchup": {"hfa": 2.0}},
        },
    )
    assert logged.status_code == 200
    body = logged.json()
    assert body["ok"] is True
    proj_id = body["projection"]["id"]
    assert body["projection"]["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION

    close = client.post(
        f"/cfb/season-engine/projections/{proj_id}/close",
        json={"close_spread_home": -4.0, "close_total": 53.5, "source": "manual"},
    )
    assert close.status_code == 200
    assert close.json()["ok"] is True
    assert close.json()["projection"]["spread_clv"] == -3.0

    result = client.post(
        f"/cfb/season-engine/projections/{proj_id}/result",
        json={"home_score": 34, "away_score": 27},
    )
    assert result.status_code == 200
    assert result.json()["ok"] is True
    assert result.json()["projection"]["grade_su"] == "win"

    perf = client.get("/cfb/season-engine/performance")
    assert perf.status_code == 200
    summary = perf.json()
    assert summary["ok"] is True
    assert summary["n_logged"] >= 1
    assert "ats" in summary
    assert "clv" in summary
    assert "tracking" in summary

    # Explicit log_projection flag on project-game does not break happy path
    proj = client.post(
        "/cfb/season-engine/project-game",
        json={
            "home_team": "TEX",
            "away_team": "OSU",
            "week": 1,
            "demo": True,
            "log_projection": True,
        },
    )
    assert proj.status_code == 200
    pdata = proj.json()
    assert pdata["ok"] is True
    assert pdata.get("projection_logged") is True
    assert pdata.get("projection_log_id")
