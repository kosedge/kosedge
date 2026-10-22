"""Synthetic W8 capture tests (AC-1..AC-11, DR-1..DR-6). No live data."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_w8_capture.constants import STATUS_FAIL, STATUS_OFFICIAL
from src.services.nfl_w8_capture.dry_run import (
    MODEL_VERSION,
    run_dry_run,
    run_tamper_suite,
    _slate,
)
from src.services.nfl_w8_capture.isolation import historical_rebuild_import_hits
from src.services.nfl_w8_capture.seal import CaptureError, build_and_seal, refuse_publish
from src.services.nfl_w8_capture.streams import validate_input_proof
from src.services.nfl_w8_capture.timeutil import et_to_utc
from src.services.nfl_w8_capture.dry_run import NOW_ET


def test_ac10_isolated_from_historical_rebuild() -> None:
    assert historical_rebuild_import_hits() == []


def test_ac11_publish_forbidden() -> None:
    with pytest.raises(CaptureError, match="AC-11"):
        refuse_publish(True)


def test_ac2_week_number_matching_refused() -> None:
    reason = validate_input_proof(
        {
            "game_id": "SYN-W8-G01",
            "input_name": "home_off_epa_5g",
            "feature_week": 7,
            "kickoff_utc": "2026-10-30T00:20:00Z",
        },
        min_lead_minutes=60,
    )
    assert reason == "week_number_matching_not_accepted"


def test_dr1_end_to_end(tmp_path: Path) -> None:
    out = run_dry_run(tmp_path / "dr1")
    assert out["ok"] is True
    assert out["receipt"]["status"] == STATUS_OFFICIAL
    assert out["receipt"]["official_seal_time_utc"]
    assert out["build"]["published"] is False
    assert out["build"]["graded"] is False
    handoff = (tmp_path / "dr1" / "blind_grade_handoff.json").read_text(encoding="utf-8")
    assert "NOT_CAPTURE_BUILDER" in handoff
    assert "null" in handoff  # outcomes omitted


def test_dr2_through_dr6_detected(tmp_path: Path) -> None:
    suite = run_tamper_suite(tmp_path / "suite")
    assert suite["all_ok"] is True
    assert suite["published"] is False
    assert suite["graded"] is False
    ids = [row["dr"] for row in suite["results"]]
    assert ids == ["DR-1", "DR-2", "DR-3", "DR-4", "DR-5", "DR-6"]
    assert all(row["ok"] for row in suite["results"])


def test_dry_run_refuses_odds_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODDS_API_KEY", "not-a-real-key")
    with pytest.raises(CaptureError, match="ODDS_API_KEY"):
        run_dry_run(tmp_path / "creds")
    monkeypatch.delenv("ODDS_API_KEY", raising=False)


def test_missing_or_late_is_fail(tmp_path: Path) -> None:
    payload = _slate()
    payload["odds_snapshots"] = []
    built = build_and_seal(
        tmp_path / "miss",
        **payload,
        model_version=MODEL_VERSION,
        code_sha="x",
        now_utc=et_to_utc(NOW_ET),
        dry_run=True,
    )
    assert built.status == STATUS_FAIL
    assert any(f.get("reason") == "missing_snapshot" for f in built.failures)
