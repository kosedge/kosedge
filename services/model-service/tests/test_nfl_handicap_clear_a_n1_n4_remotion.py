"""CLEAR-A remotion v3 — N1–N4 Codex/IMV probes (D2 remainder).

D1/D3/D4 validator paths stay closed. No infra/db, no live wiring, no capture.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_handicap_ledger import (
    FORECAST_HANDICAP_DELTA,
    FORECAST_HANDICAPPED_FAIR,
    FORECAST_INDEPENDENT_FAIR,
    L0_LAYER,
    L1_LAYER,
    LEDGER_SCHEMA_VERSION,
    AppendOnlyHandicapLedger,
    HandicapLedgerEnvelope,
    HandicapLedgerReject,
    canonicalize_as_of_ts,
    commit_l1_stage,
    make_prediction_id,
)
from src.services.nfl_handicap_ledger.validate import envelope_from_row


DECISION_TS = "2026-10-29T16:00:00Z"


def _l1_raw(**overrides: object) -> dict:
    row = {
        "game_id": "n1-l1",
        "capture_id": "cap-n1",
        "as_of_ts": "2026-10-25T15:00:00Z",
        "baseline_ref": "baseline-personnel-ref-dev",
        "registry_id": "reg-n1",
        "source_snapshot_id": "snap-n1",
        "factor": "injury_availability",
        "entry_point": "points",
        "delta": 0.0,
        "uncertainty": 0.0,
        "missing": True,
        "forecast_label": FORECAST_HANDICAP_DELTA,
        "decision_ts": DECISION_TS,
        "model_version": "nfl-v1.5-matchup-sim",
    }
    row.update(overrides)
    return row


def _l0_raw(**overrides: object) -> dict:
    row = {
        "game_id": "n1-l0",
        "model_version": "nfl-v1.5-matchup-sim",
        "as_of_ts": "2026-10-25T15:00:00Z",
        "capture_id": "cap-n1-l0",
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


def _valid_l1_envelope(**overrides: object) -> HandicapLedgerEnvelope:
    return envelope_from_row(
        _l1_raw(**overrides),
        layer=L1_LAYER,
        forecast_label=FORECAST_HANDICAP_DELTA,
        decision_ts=DECISION_TS,
    )


def test_n1_envelope_l1_hf_naive_empty_rejected(tmp_path: Path) -> None:
    """N1: public Envelope L1/HF/naive/empty payload REJECT."""
    store = AppendOnlyHandicapLedger(tmp_path / "n1.jsonl")
    bad = HandicapLedgerEnvelope(
        prediction_id="hl_probe",
        layer=L1_LAYER,
        forecast_label=FORECAST_HANDICAPPED_FAIR,
        game_id="g-n1",
        as_of_ts="2026-10-29T15:00:00",
        decision_ts="x",
        capture_id="cap",
        source_snapshot_id=None,
        registry_id=None,
        baseline_ref=None,
        model_version="",
        payload={},
    )
    before = len(store)
    with pytest.raises(HandicapLedgerReject, match="REJECT"):
        store.append(bad)
    assert len(store) == before


def test_n1_envelope_l0_payload_blend_not_zero_rejected(tmp_path: Path) -> None:
    """N1: L0 Envelope with payload market_blend=0.3 REJECT."""
    store = AppendOnlyHandicapLedger(tmp_path / "n1-l0.jsonl")
    raw = _l0_raw(market_blend=0)
    env = envelope_from_row(
        raw,
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        decision_ts=DECISION_TS,
    )
    dirty = HandicapLedgerEnvelope(
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


def test_n2_append_many_intra_batch_duplicate_rejected(tmp_path: Path) -> None:
    """N2: append_many([e, e]) REJECT, len unchanged."""
    store = AppendOnlyHandicapLedger(tmp_path / "n2.jsonl")
    env = _valid_l1_envelope()
    before = len(store)
    with pytest.raises(HandicapLedgerReject, match="duplicate"):
        store.append_many([env, env])
    assert len(store) == before
    assert store.rows() == []


def test_n3_same_instant_as_of_spellings_share_identity(tmp_path: Path) -> None:
    """N3: Z / +00:00 / -04:00 same instant → 2nd and 3rd REJECT."""
    store = AppendOnlyHandicapLedger(tmp_path / "n3.jsonl")
    stamps = (
        "2026-10-25T15:00:00Z",
        "2026-10-25T15:00:00+00:00",
        "2026-10-25T11:00:00-04:00",
    )
    assert len({canonicalize_as_of_ts(s) for s in stamps}) == 1
    ids = [
        make_prediction_id(
            layer=L1_LAYER,
            forecast_label=FORECAST_HANDICAP_DELTA,
            game_id="n3-l1",
            as_of_ts=s,
            capture_id="cap-n3",
            schema_version=LEDGER_SCHEMA_VERSION,
        )
        for s in stamps
    ]
    assert ids[0] == ids[1] == ids[2]
    commit_l1_stage(store, [_l1_raw(as_of_ts=stamps[0], delta=0.0, game_id="n3-l1", capture_id="cap-n3")], decision_ts=DECISION_TS)
    assert len(store) == 1
    with pytest.raises(HandicapLedgerReject, match="duplicate"):
        commit_l1_stage(
            store,
            [_l1_raw(as_of_ts=stamps[1], delta=1.5, game_id="n3-l1", capture_id="cap-n3")],
            decision_ts=DECISION_TS,
        )
    with pytest.raises(HandicapLedgerReject, match="duplicate"):
        commit_l1_stage(
            store,
            [_l1_raw(as_of_ts=stamps[2], delta=9.0, game_id="n3-l1", capture_id="cap-n3")],
            decision_ts=DECISION_TS,
        )
    assert len(store) == 1


def test_n4_jsonl_load_rejects_forged_prediction_id(tmp_path: Path) -> None:
    """N4: JSONL load re-validates and re-derives; forged id REJECT."""
    store = AppendOnlyHandicapLedger(tmp_path / "n4-ok.jsonl")
    written = commit_l1_stage(store, [_l1_raw(game_id="n4-l1")], decision_ts=DECISION_TS)
    assert len(written) == 1
    path = tmp_path / "n4-forged.jsonl"
    forged = dict(written[0])
    forged["prediction_id"] = "hl_forged"
    path.write_text(json.dumps(forged, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(HandicapLedgerReject, match="forged prediction_id|caller-chosen"):
        AppendOnlyHandicapLedger(path)
    # Unvalidated stub row also rejects (no last-wins / no silent accept).
    stub = tmp_path / "n4-stub.jsonl"
    stub.write_text(json.dumps({"prediction_id": "hl_forged", "layer": "L1"}) + "\n", encoding="utf-8")
    with pytest.raises(HandicapLedgerReject, match="REJECT"):
        AppendOnlyHandicapLedger(stub)
