"""G1–G8 forecast emit + t4559u W8 input completeness (no Odds, no seals)."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from src.services.nfl_model_forecast_emit.binding import bind_forecast_to_seal_hook
from src.services.nfl_model_forecast_emit.completeness import audit_week_inputs
from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    canonicalize,
    emit_model_forecast,
)
from src.services.nfl_model_forecast_emit.engine_adapter import (
    inputs_from_engine_projection,
)
from src.services.nfl_model_forecast_emit.schema import (
    CERT_CANDIDATE,
    EVAL_RECORD_PAPER_SHA8,
    LABEL,
    SCHEMA_VERSION,
    SPREAD_SIGN_CONVENTION,
)
from src.services.nfl_model_forecast_emit.slate import run_week_slate

TIP = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
FP = {"pack_sha256": "b" * 64}


def _base_inputs(**overrides):
    payload = {
        "game_id": "2026-W08-CAR@GB",
        "home_team": "GB",
        "away_team": "CAR",
        "kickoff_utc": "2026-10-30T00:15:00Z",
        "forecast_ts_utc": "2026-10-27T21:00:00Z",
        "latest_input_as_of": "2026-10-27T20:00:00Z",
        "code_tip_sha": TIP,
        "model": {"identity": "nfl-season-engine", "version": "test-engine"},
        "markets": {
            "spread": {
                "prediction": -3.5,
                "ref_line": -3.5,
                "ref_line_source": "nfl-season-engine:test.spread_home",
                "orientation": "home",
                "sign_convention": SPREAD_SIGN_CONVENTION,
            },
            "total": {
                "prediction": 44.0,
                "ref_line": 44.0,
                "ref_line_source": "nfl-season-engine:test.total_mean",
            },
            "moneyline": {
                "prediction": 0.61,
                "ref_line": 0.61,
                "ref_line_source": "nfl-season-engine:test.home_win_prob",
            },
        },
        "input_provenance": {"fingerprints": FP},
    }
    payload.update(overrides)
    return payload


def test_emit_complete_artifact_g1_g8(tmp_path: Path) -> None:
    dest = tmp_path / "2026-W08-CAR@GB.json"
    art = emit_model_forecast(_base_inputs(), dest_path=dest)
    assert art["schema_version"] == SCHEMA_VERSION
    assert art["cert_candidate"] == 0
    assert art["label"] == LABEL
    assert art["eval_record_paper_sha8"] == EVAL_RECORD_PAPER_SHA8
    assert art["game_id"] == "2026-W08-CAR@GB"
    assert art["home_team"] == "GB" and art["away_team"] == "CAR"
    assert art["kickoff_utc"] == "2026-10-30T00:15:00Z"
    assert art["lead_seconds"] == 51 * 3600 + 15 * 60
    assert art["pre_kickoff"] is True
    assert art["latest_input_as_of"] == "2026-10-27T20:00:00Z"
    assert art["code_tip_sha"] == TIP
    assert len(art["config_sha256"]) == 64
    assert art["orientation"]["spread_sign_convention"] == SPREAD_SIGN_CONVENTION
    assert art["markets"]["spread"]["prediction"] == -3.5
    assert art["markets"]["spread"]["ref_line"] == -3.5
    assert art["markets"]["spread"]["ref_line_source"]
    assert art["grades"] == {"ats": None, "ou": None, "su": None}
    assert art["missing_inputs"] == []
    assert art["inputs_complete"] is True
    assert art["close_anchor"]["status"] == "reserved_empty"
    assert art["close_anchor"]["close_spread_home"] is None
    blob = dest.read_bytes()
    assert b'"cert_candidate":0' in blob
    assert f'"label":"{LABEL}"'.encode() in blob
    sidecar = dest.with_name(dest.name + ".record_sha256")
    assert sidecar.is_file()
    digest = sidecar.read_text(encoding="utf-8").strip()
    assert len(digest) == 64
    assert stat.S_IMODE(dest.stat().st_mode) == 0o444
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o444


def test_g1_home_away_mismatch_refused() -> None:
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(home_team="CAR", away_team="GB"))
    assert ei.value.gap == "G1"


def test_g1_missing_kickoff_refused() -> None:
    payload = _base_inputs()
    del payload["kickoff_utc"]
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(payload)
    assert ei.value.gap == "G1"


def test_g2_input_after_forecast_refused() -> None:
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(latest_input_as_of="2026-10-27T22:00:00Z"))
    assert ei.value.gap == "G2"


def test_g2_after_kickoff_refused() -> None:
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(forecast_ts_utc="2026-10-30T00:15:00Z"))
    assert ei.value.gap == "G2"


def test_g3_missing_ref_line_source_refused() -> None:
    payload = _base_inputs()
    payload["markets"]["spread"] = {"prediction": -3.5, "ref_line": -3.5, "ref_line_source": ""}
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(payload)
    assert ei.value.gap == "G3"


def test_g4_short_tip_sha_refused() -> None:
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(code_tip_sha="385767a2"))
    assert ei.value.gap == "G4"


def test_g6_refuse_overwrite(tmp_path: Path) -> None:
    dest = tmp_path / "once.json"
    emit_model_forecast(_base_inputs(), dest_path=dest)
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(), dest_path=dest)
    assert ei.value.gap == "G6"


def test_g6_refuse_seal_dest(tmp_path: Path) -> None:
    dest = tmp_path / "seals" / "w8_first_seal_b_t4525u_a896cfd0" / "x.json"
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(), dest_path=dest)
    assert ei.value.reason == "seal_dest_refused"


def test_g7_close_input_refused() -> None:
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(_base_inputs(close_spread_home=-3.0))
    assert ei.value.gap == "G7"


def test_missing_input_flags_are_explicit() -> None:
    art = emit_model_forecast(
        _base_inputs(
            missing_inputs=[
                {"name": "injury_paths_current", "reason": "empty"},
                {"name": "depth_sot_week", "reason": "week=1"},
            ]
        )
    )
    assert art["inputs_complete"] is False
    assert [m["name"] for m in art["missing_inputs"]] == [
        "injury_paths_current",
        "depth_sot_week",
    ]


def test_g8_unset_prediction_refused() -> None:
    payload = _base_inputs()
    payload["markets"]["spread"]["prediction"] = "UNSET"
    payload["markets"]["spread"]["ref_line"] = "UNSET"
    with pytest.raises(ForecastIncompleteError) as ei:
        emit_model_forecast(payload)
    assert ei.value.gap == "G8"


def test_engine_adapter_from_game_script() -> None:
    proj = {
        "game_id": "2026-W08-CAR@GB",
        "home_team": "GB",
        "away_team": "CAR",
        "engine_version": "nfl-season-engine-test",
        "n_replicates": 80,
        "notes": {"pack_sha256": "c" * 64, "snapshot_id": "snap-1"},
        "game_script_summary": {
            "expected_home_score_mean": 24.0,
            "expected_away_score_mean": 20.5,
            "expected_total_mean": 44.5,
            "home_win_prob_mean": 0.62,
        },
    }
    inputs = inputs_from_engine_projection(
        proj,
        kickoff_utc="2026-10-30T00:15:00Z",
        latest_input_as_of="2026-10-27T20:00:00Z",
        code_tip_sha=TIP,
    )
    assert inputs["markets"]["spread"]["prediction"] == -3.5
    art = emit_model_forecast(inputs)
    assert art["markets"]["moneyline"]["prediction"] == 0.62


def test_bind_hook_game_id_and_cert() -> None:
    art = emit_model_forecast(_base_inputs())
    hook = bind_forecast_to_seal_hook(art, seal_game_id="2026-W08-CAR@GB")
    assert hook["cert_candidate"] == 0
    assert hook["status"] == "unbound"
    with pytest.raises(ForecastIncompleteError):
        bind_forecast_to_seal_hook(art, seal_game_id="2026-W08-PHI@WAS")


def test_w8_packaged_inputs_are_incomplete() -> None:
    report = audit_week_inputs(season=2026, week=8, now_utc="2026-10-27T21:15:00Z")
    assert report["cert_candidate"] == CERT_CANDIDATE
    assert report["ok"] is False
    assert "depth_sot_week" in report["failing_components"]
    assert "injury_paths_current" in report["failing_components"]
    assert "current_weekly_depth_db" in report["failing_components"]
    assert "inseason_efficiency_current" in report["failing_components"]
    assert "week_schedule_kickoffs" in report["passed"]
    assert "2026-W08-CAR@GB" in report["slate_game_ids"]
    assert "2026-W08-PHI@WAS" in report["slate_game_ids"]
    with pytest.raises(ForecastIncompleteError) as ei:
        run_week_slate(season=2026, week=8, now_utc="2026-10-27T21:15:00Z")
    assert ei.value.reason == "slate_inputs_incomplete"


def test_module_source_has_no_odds_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_model_forecast_emit"
    for path in root.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                lowered = stripped.lower()
                assert "odds_api" not in lowered
                assert "the-odds-api" not in lowered
