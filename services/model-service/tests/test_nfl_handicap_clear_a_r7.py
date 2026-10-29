"""CLEAR-A R7 — JSONL load top-level vs payload must not bypass validation.

IMV a9d44516 residual: L0 disk row with top-level market_blend=0 and
payload.market_blend=0.3 loaded because _field_from preferred top-level.
Append already REJECTS (N1). Load must fail closed on the same contamination.

Do not reopen N1–N4 / D1–D4. No infra/db, no live wiring, no capture.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_handicap_ledger import (
    FORECAST_INDEPENDENT_FAIR,
    L0_LAYER,
    AppendOnlyHandicapLedger,
    HandicapLedgerReject,
    validate_l0_row,
)
from src.services.nfl_handicap_ledger.validate import envelope_from_row


DECISION_TS = "2026-10-29T16:00:00Z"
R7_REJECT = "conflicts with payload|market_blend MUST = 0"


def _l0_raw(**overrides: object) -> dict:
    row = {
        "game_id": "r7-l0",
        "model_version": "nfl-v1.5-matchup-sim",
        "as_of_ts": "2026-10-25T15:00:00Z",
        "capture_id": "cap-r7-l0",
        "baseline_personnel_ref": "baseline-personnel-ref-dev",
        "off_eff_h": 1.0,
        "off_eff_a": 1.0,
        "def_eff_h": 1.0,
        "def_eff_a": 1.0,
        "pace_h": 1.0,
        "pace_a": 1.0,
        "margin_mu": 0.16,
        "total_mu": 43.82,
        "sigma": 9.1,
        "market_blend": 0,
        "forecast_label": FORECAST_INDEPENDENT_FAIR,
        "decision_ts": DECISION_TS,
    }
    row.update(overrides)
    return row


def _write_clean_l0(path: Path) -> dict:
    store = AppendOnlyHandicapLedger(path)
    written = store.append_layer(
        _l0_raw(),
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        decision_ts=DECISION_TS,
    )
    assert len(store) == 1
    return written


def _tamper_disk_row(clean: dict, *, top_blend: object, payload_blend: object) -> dict:
    dirty = dict(clean)
    dirty["market_blend"] = top_blend
    payload = dict(clean.get("payload") or {})
    payload["market_blend"] = payload_blend
    dirty["payload"] = payload
    return dirty


def test_r7_jsonl_load_rejects_top_zero_payload_dirty_blend(tmp_path: Path) -> None:
    """IMV probe: top-level 0 + payload 0.3 must REJECT on load (no silent accept)."""
    clean_path = tmp_path / "r7-clean.jsonl"
    written = _write_clean_l0(clean_path)
    dirty_path = tmp_path / "r7-contam.jsonl"
    dirty = _tamper_disk_row(written, top_blend=0, payload_blend=0.3)
    dirty_path.write_text(json.dumps(dirty, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(HandicapLedgerReject, match=R7_REJECT):
        AppendOnlyHandicapLedger(dirty_path)
    with pytest.raises(HandicapLedgerReject, match=R7_REJECT):
        validate_l0_row(dirty)


def test_r7_jsonl_load_rejects_payload_only_dirty_blend(tmp_path: Path) -> None:
    """Payload-only market_blend=0.3 on disk REJECT (no top-level mask)."""
    written = _write_clean_l0(tmp_path / "r7-clean2.jsonl")
    dirty = dict(written)
    payload = dict(written.get("payload") or {})
    payload["market_blend"] = 0.3
    dirty["payload"] = payload
    dirty.pop("market_blend", None)
    path = tmp_path / "r7-payload-only.jsonl"
    path.write_text(json.dumps(dirty, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(HandicapLedgerReject, match="market_blend MUST = 0"):
        AppendOnlyHandicapLedger(path)


def test_r7_jsonl_load_rejects_top_dirty_payload_zero(tmp_path: Path) -> None:
    """Top-level 0.3 + payload 0 is also contamination; no precedence either way."""
    written = _write_clean_l0(tmp_path / "r7-clean3.jsonl")
    dirty = _tamper_disk_row(written, top_blend=0.3, payload_blend=0)
    path = tmp_path / "r7-top-dirty.jsonl"
    path.write_text(json.dumps(dirty, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(HandicapLedgerReject, match=R7_REJECT):
        AppendOnlyHandicapLedger(path)


def test_r7_jsonl_load_rejects_conflicting_margin_mu(tmp_path: Path) -> None:
    """Any top-level vs payload conflict rejects; not just market_blend."""
    written = _write_clean_l0(tmp_path / "r7-clean4.jsonl")
    dirty = dict(written)
    payload = dict(written.get("payload") or {})
    dirty["margin_mu"] = 0.16
    payload["margin_mu"] = 9.99
    dirty["payload"] = payload
    path = tmp_path / "r7-margin-conflict.jsonl"
    path.write_text(json.dumps(dirty, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(HandicapLedgerReject, match="conflicts with payload"):
        AppendOnlyHandicapLedger(path)


def test_r7_clean_l0_write_reload_accepts_same_identity(tmp_path: Path) -> None:
    """Clean append + JSONL reload still ACCEPT; prediction_id unchanged."""
    path = tmp_path / "r7-reload.jsonl"
    written = _write_clean_l0(path)
    pid = written["prediction_id"]
    assert pid.startswith("hl_")
    reloaded = AppendOnlyHandicapLedger(path)
    assert len(reloaded) == 1
    row = reloaded.rows()[0]
    assert row["prediction_id"] == pid
    assert row["layer"] == L0_LAYER
    assert row["forecast_label"] == FORECAST_INDEPENDENT_FAIR
    assert row["payload"]["market_blend"] == 0
    assert "market_blend" not in row or row.get("market_blend") in (None, 0, 0.0)
    env = envelope_from_row(
        written,
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        decision_ts=DECISION_TS,
    )
    assert env.prediction_id == pid


def test_r7_append_still_rejects_dirty_payload_blend(tmp_path: Path) -> None:
    """N1 preserved: append / append_many still REJECT dirty payload blend."""
    store = AppendOnlyHandicapLedger(tmp_path / "r7-append.jsonl")
    raw = _l0_raw(market_blend=0)
    env = envelope_from_row(
        raw,
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        decision_ts=DECISION_TS,
    )
    dirty = type(env)(
        **{
            **env.to_dict(),
            "payload": {**dict(env.payload), "market_blend": 0.3},
        }
    )
    with pytest.raises(HandicapLedgerReject, match="market_blend MUST = 0"):
        store.append(dirty)
    assert len(store) == 0
    with pytest.raises(HandicapLedgerReject, match="market_blend MUST = 0"):
        store.append_many([dirty])
    assert len(store) == 0
