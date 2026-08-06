"""Historical calibration reports from proof-layer JSONL lake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.proof_layer.calibration_report import (
    THIN_SAMPLE_THRESHOLD,
    build_calibration_report,
    generate_calibration_report,
    load_filtered_projections,
    write_report_artifact,
)
from src.services.proof_layer.core import log_projection, record_close, record_result


def _seed_game(
    lake: Path,
    *,
    sport: str,
    home: str,
    away: str,
    week: int,
    spread: float,
    total: float,
    close_spread: float,
    close_total: float,
    home_score: int,
    away_score: int,
    engine_version: str = "test-engine-v1",
    projected_at: str | None = None,
) -> str:
    payload = {
        "sport": sport,
        "home_team": home,
        "away_team": away,
        "season": 2026,
        "week": week,
        "engine_version": engine_version,
        "spread_home": spread,
        "expected_total": total,
        "home_win_prob": 0.55 if spread < 0 else 0.45,
    }
    if projected_at:
        payload["projected_at"] = projected_at
    rec = log_projection(payload, sport=sport, lake_dir=lake)
    record_close(
        rec.id,
        close_spread_home=close_spread,
        close_total=close_total,
        lake_dir=lake,
    )
    record_result(rec.id, home_score=home_score, away_score=away_score, lake_dir=lake)
    return rec.id


def test_thin_sample_honesty_flag(tmp_path) -> None:
    lake = tmp_path / "thin"
    _seed_game(
        lake,
        sport="nfl",
        home="KC",
        away="BUF",
        week=1,
        spread=-3.0,
        total=48.0,
        close_spread=-2.5,
        close_total=47.0,
        home_score=27,
        away_score=20,
    )

    report = build_calibration_report(sport="nfl", lake_dir=lake)
    assert report["ok"] is True
    assert report["metrics"]["n_with_result"] == 1
    assert "thin_sample" in report["honesty_flags"]
    assert "thin sample" in report["summary_text"].lower()


def test_adequate_sample_no_thin_flag(tmp_path) -> None:
    lake = tmp_path / "adequate"
    for i in range(THIN_SAMPLE_THRESHOLD):
        week = (i % 18) + 1
        spread = -3.5 if i % 2 == 0 else 2.5
        _seed_game(
            lake,
            sport="cfb",
            home="ALA",
            away=f"T{i:02d}",
            week=week,
            spread=spread,
            total=50.0 + (i % 5),
            close_spread=spread + 0.5,
            close_total=49.0,
            home_score=28 + (i % 3),
            away_score=21 + (i % 4),
            engine_version="cfb-test-v1",
        )

    report = build_calibration_report(sport="cfb", lake_dir=lake)
    assert report["metrics"]["n_with_result"] == THIN_SAMPLE_THRESHOLD
    assert "thin_sample" not in report["honesty_flags"]
    assert report["metrics"]["ats"]["n"] >= THIN_SAMPLE_THRESHOLD - 5


def test_bias_slices_home_favorite_vs_dog(tmp_path) -> None:
    lake = tmp_path / "bias"
    # Home favorites
    for i in range(8):
        _seed_game(
            lake,
            sport="nfl",
            home="KC",
            away=f"A{i}",
            week=2,
            spread=-7.0,
            total=45.0,
            close_spread=-6.0,
            close_total=44.5,
            home_score=31,
            away_score=17,
        )
    # Home dogs
    for i in range(6):
        _seed_game(
            lake,
            sport="nfl",
            home="NYJ",
            away=f"B{i}",
            week=3,
            spread=4.0,
            total=42.0,
            close_spread=3.5,
            close_total=41.5,
            home_score=14,
            away_score=24,
        )

    report = build_calibration_report(sport="nfl", lake_dir=lake)
    bias = report["bias_slices"]
    assert bias["home_favorite"]["n_with_result"] == 8
    assert bias["home_dog"]["n_with_result"] == 6
    assert bias["home_favorite"]["thin_sample"] is True
    assert "home favorite" in report["summary_text"].lower()


def test_early_season_slice(tmp_path) -> None:
    lake = tmp_path / "early"
    _seed_game(
        lake,
        sport="cfb",
        home="UGA",
        away="TEX",
        week=2,
        spread=-2.5,
        total=52.0,
        close_spread=-3.0,
        close_total=51.0,
        home_score=35,
        away_score=28,
    )
    _seed_game(
        lake,
        sport="cfb",
        home="OSU",
        away="MICH",
        week=10,
        spread=-1.5,
        total=48.0,
        close_spread=-2.0,
        close_total=47.5,
        home_score=24,
        away_score=21,
    )

    report = build_calibration_report(sport="cfb", lake_dir=lake)
    assert report["bias_slices"]["early_season_week_le_4"]["n_with_result"] == 1
    assert report["bias_slices"]["mid_late_season_week_gt_4"]["n_with_result"] == 1


def test_filter_by_engine_version_and_season(tmp_path) -> None:
    lake = tmp_path / "filters"
    _seed_game(
        lake,
        sport="nfl",
        home="SF",
        away="LA",
        week=1,
        spread=-1.0,
        total=44.0,
        close_spread=-1.5,
        close_total=43.5,
        home_score=20,
        away_score=17,
        engine_version="nfl-v1",
    )
    _seed_game(
        lake,
        sport="nfl",
        home="DAL",
        away="PHI",
        week=1,
        spread=-2.0,
        total=46.0,
        close_spread=-2.5,
        close_total=45.5,
        home_score=24,
        away_score=21,
        engine_version="nfl-v2",
    )

    rows = load_filtered_projections(sport="nfl", engine_version="nfl-v1", lake_dir=lake)
    assert len(rows) == 1
    assert rows[0].engine_version == "nfl-v1"


def test_write_artifact(tmp_path) -> None:
    lake = tmp_path / "artifact_lake"
    report_dir = tmp_path / "reports"
    _seed_game(
        lake,
        sport="nfl",
        home="BUF",
        away="MIA",
        week=1,
        spread=-4.0,
        total=47.0,
        close_spread=-3.5,
        close_total=46.5,
        home_score=30,
        away_score=21,
    )
    out = generate_calibration_report(
        sport="nfl",
        lake_dir=lake,
        write_artifact=True,
        report_dir=report_dir,
    )
    assert out.get("artifact_path")
    path = Path(out["artifact_path"])
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["report_type"] == "historical_calibration"


def test_calibration_report_http_endpoints(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "jsonl")
    monkeypatch.setenv("PROJECTION_LOG_BACKEND", "jsonl")
    monkeypatch.setenv("PROJECTION_LOG_DIR", str(tmp_path / "http_cal"))
    import src.services.proof_layer.core as core

    monkeypatch.setattr(core, "LAKE_DIR", tmp_path / "http_cal")

    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    lake = tmp_path / "http_cal"
    _seed_game(
        lake,
        sport="cfb",
        home="CLEM",
        away="FSU",
        week=1,
        spread=-5.0,
        total=54.0,
        close_spread=-4.5,
        close_total=53.5,
        home_score=38,
        away_score=28,
    )

    get_resp = client.get("/proof/calibration-report?sport=cfb")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["ok"] is True
    assert body["report_type"] == "historical_calibration"
    assert "thin_sample" in body["honesty_flags"]

    post_resp = client.post(
        "/proof/calibration-report/generate",
        json={"sport": "cfb"},
    )
    assert post_resp.status_code == 200
    post_body = post_resp.json()
    assert post_body.get("artifact_path")


def test_no_closes_honesty_flag(tmp_path) -> None:
    lake = tmp_path / "no_close"
    rec = log_projection(
        {
            "sport": "nfl",
            "home_team": "GB",
            "away_team": "CHI",
            "season": 2026,
            "week": 5,
            "spread_home": -3.0,
            "expected_total": 42.0,
            "home_win_prob": 0.6,
        },
        sport="nfl",
        lake_dir=lake,
    )
    record_result(rec.id, home_score=24, away_score=17, lake_dir=lake)

    report = build_calibration_report(sport="nfl", lake_dir=lake)
    assert "no_closes" in report["honesty_flags"]
    assert report["metrics"]["clv"]["n_spread"] == 0
