"""CLEAR-A remotion D1–D4 — Codex blocker probes (F1–F7, F9, F11, F13).

Each test reproduces a filed probe and asserts REJECT after remotion.
R1/F8 and R2/F10 remain NON_BLOCKING residuals (comments only).
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
    FORECAST_MARKET_INFORMED_FAIR,
    L0_LAYER,
    L1_LAYER,
    L4_LAYER,
    LEDGER_SCHEMA_VERSION,
    AppendOnlyHandicapLedger,
    HandicapLedgerEnvelope,
    HandicapLedgerReject,
    commit_l1_stage,
    is_exact_zero,
    make_prediction_id,
    validate_l0_row,
    validate_l1_row,
    validate_l4_row,
)
from src.services.nfl_simulator import independent_fair_mus


DECISION_TS = "2026-10-29T16:00:00Z"


def _l1_ok(**overrides: object) -> dict:
    row = {
        "game_id": "d3-remotion-l1",
        "capture_id": "cap-remotion-1",
        "as_of_ts": "2026-10-29T15:00:00Z",
        "baseline_ref": "baseline-personnel-ref-dev",
        "registry_id": "reg-clear-a-l1",
        "source_snapshot_id": "snap-remotion-1",
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


def _l0_ok(**overrides: object) -> dict:
    row = {
        "game_id": "d3-remotion-l0",
        "model_version": "nfl-v1.5-matchup-sim",
        "as_of_ts": "2026-10-29T15:00:00Z",
        "capture_id": "cap-remotion-l0",
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


def test_f1_l0_market_blend_exact_zero_rejects_bool_and_fraction() -> None:
    """F1: int(0.3)==0 and int(False)==0 must not fail-open."""
    assert is_exact_zero(0) is True
    assert is_exact_zero(0.0) is True
    assert is_exact_zero(0.3) is False
    assert is_exact_zero(False) is False
    assert is_exact_zero(True) is False
    validate_l0_row(_l0_ok(market_blend=0))
    validate_l0_row(_l0_ok(market_blend=0.0))
    with pytest.raises(HandicapLedgerReject, match="market_blend MUST = 0"):
        validate_l0_row(_l0_ok(market_blend=0.3))
    with pytest.raises(HandicapLedgerReject, match="market_blend MUST = 0"):
        validate_l0_row(_l0_ok(market_blend=False))


def test_f2_append_caller_chosen_id_bypasses_rejected(tmp_path: Path) -> None:
    """F2: store.append with attacker id + junk payload ⇒ REJECT."""
    store = AppendOnlyHandicapLedger(tmp_path / "f2.jsonl")
    with pytest.raises(HandicapLedgerReject, match="unvalidated"):
        store.append(
            {
                "prediction_id": "hl_attacker_chosen",
                "layer": "L1",
                "forecast_label": "independent_fair",
                "payload": {"junk": True},
            }
        )
    assert len(store) == 0
    env = HandicapLedgerEnvelope(
        prediction_id="hl_attacker_chosen",
        layer=L1_LAYER,
        forecast_label=FORECAST_HANDICAP_DELTA,
        game_id="g-attacker",
        as_of_ts="2026-10-29T15:00:00Z",
        decision_ts=DECISION_TS,
        capture_id="cap-attacker",
        source_snapshot_id="snap",
        registry_id="reg",
        baseline_ref="base",
        model_version="nfl-v1.5-matchup-sim",
    )
    with pytest.raises(HandicapLedgerReject, match="caller-chosen"):
        store.append(env)
    assert len(store) == 0


def test_f3_jsonl_reload_duplicate_id_rejected_not_last_wins(tmp_path: Path) -> None:
    """F3: duplicate prediction_id on disk ⇒ load REJECT (no last-wins)."""
    path = tmp_path / "dup.jsonl"
    path.write_text(
        json.dumps({"prediction_id": "same", "n": 1})
        + "\n"
        + json.dumps({"prediction_id": "same", "n": 2})
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(HandicapLedgerReject, match="no last-wins"):
        AppendOnlyHandicapLedger(path)


def test_f4_business_identity_unique_ignores_payload_delta(tmp_path: Path) -> None:
    """F4: same L1 business key, delta 0.0 then 1.5 ⇒ second REJECT."""
    store = AppendOnlyHandicapLedger(tmp_path / "f4.jsonl")
    first = _l1_ok(delta=0.0)
    second = _l1_ok(delta=1.5)
    commit_l1_stage(store, [first], decision_ts=DECISION_TS)
    assert len(store) == 1
    id1 = make_prediction_id(
        layer=L1_LAYER,
        forecast_label=FORECAST_HANDICAP_DELTA,
        game_id=first["game_id"],
        as_of_ts=first["as_of_ts"],
        capture_id=first["capture_id"],
        schema_version=LEDGER_SCHEMA_VERSION,
    )
    id2 = make_prediction_id(
        layer=L1_LAYER,
        forecast_label=FORECAST_HANDICAP_DELTA,
        game_id=second["game_id"],
        as_of_ts=second["as_of_ts"],
        capture_id=second["capture_id"],
        schema_version=LEDGER_SCHEMA_VERSION,
    )
    assert id1 == id2
    with pytest.raises(HandicapLedgerReject, match="duplicate"):
        commit_l1_stage(store, [second], decision_ts=DECISION_TS)
    assert len(store) == 1


def test_f5_naive_and_mixed_offset_timestamps_reject() -> None:
    """F5: naive stamps rejected; mixed-offset aware compare works."""
    with pytest.raises(HandicapLedgerReject, match="naive"):
        validate_l1_row(
            _l1_ok(as_of_ts="2026-10-29T17:00:00"),
            decision_ts="2026-10-29T16:00:00-04:00",
        )
    with pytest.raises(HandicapLedgerReject, match="naive"):
        validate_l1_row(
            _l1_ok(as_of_ts="2026-10-29T15:00:00-04:00"),
            decision_ts="2026-10-29T16:00:00",
        )
    # as_of 15:00-04:00 = 19:00Z > decision 16:00Z
    with pytest.raises(HandicapLedgerReject, match="as_of_ts > decision_ts"):
        validate_l1_row(
            _l1_ok(as_of_ts="2026-10-29T15:00:00-04:00"),
            decision_ts="2026-10-29T16:00:00Z",
        )
    # as_of 15:00-04:00 = 19:00Z < decision 20:00Z
    validate_l1_row(
        _l1_ok(as_of_ts="2026-10-29T15:00:00-04:00"),
        decision_ts="2026-10-29T20:00:00Z",
    )


def test_f6_no_impute_as_of_baseline_refs_or_if_mu() -> None:
    """F6: as_of/baseline_ref/refs/IF mu are not invented."""
    l4 = {
        "game_id": "g-l4",
        "capture_id": "cap-l4",
        "market_snapshot_id": "mkt-1",
        "captured_at": "2026-10-29T15:30:00Z",
        "forecast_label": FORECAST_MARKET_INFORMED_FAIR,
        # as_of_ts omitted — must not fall back to captured_at
    }
    with pytest.raises(HandicapLedgerReject, match="missing required"):
        validate_l4_row(l4, decision_ts=DECISION_TS)

    l1_smear = _l1_ok()
    l1_smear.pop("baseline_ref")
    l1_smear["baseline_personnel_ref"] = "baseline-personnel-ref-dev"
    with pytest.raises(HandicapLedgerReject, match="baseline_ref"):
        validate_l1_row(l1_smear, decision_ts=DECISION_TS)

    with pytest.raises(ValueError, match="no impute"):
        independent_fair_mus(
            {
                "independent_fair": {
                    "forecast_label": "independent_fair",
                    "market_blend": 0,
                }
            }
        )


def test_f7_blueprint_l1_and_l0_required_sets() -> None:
    """F7: factor/entry_point/delta/uncertainty required; L0 set expanded."""
    for field in ("factor", "entry_point", "delta", "uncertainty"):
        bad = _l1_ok()
        bad.pop(field)
        with pytest.raises(HandicapLedgerReject, match="missing required"):
            validate_l1_row(bad, decision_ts=DECISION_TS)
    l0 = _l0_ok()
    l0.pop("off_eff_h")
    with pytest.raises(HandicapLedgerReject, match="missing required"):
        validate_l0_row(l0)
    l0b = _l0_ok()
    l0b.pop("sigma")
    with pytest.raises(HandicapLedgerReject, match="missing required"):
        validate_l0_row(l0b)


def test_f9_l1_not_labeled_hf_and_l4_requires_mif() -> None:
    """F9: L1 cannot be handicapped_fair; L4 empty/wrong label rejected."""
    with pytest.raises(HandicapLedgerReject, match="handicap_delta"):
        validate_l1_row(
            _l1_ok(forecast_label=FORECAST_HANDICAPPED_FAIR),
            decision_ts=DECISION_TS,
        )
    l4_empty = {
        "game_id": "g-l4",
        "capture_id": "cap-l4",
        "as_of_ts": "2026-10-29T15:00:00Z",
        "market_snapshot_id": "mkt-1",
        "captured_at": "2026-10-29T15:30:00Z",
        "forecast_label": "",
    }
    with pytest.raises(HandicapLedgerReject, match="missing required|market_informed_fair"):
        validate_l4_row(l4_empty, decision_ts=DECISION_TS)
    l4_if = dict(l4_empty)
    l4_if["forecast_label"] = FORECAST_INDEPENDENT_FAIR
    with pytest.raises(HandicapLedgerReject, match="market_informed_fair"):
        validate_l4_row(l4_if, decision_ts=DECISION_TS)


def test_f11_missing_identity_is_ledger_reject_not_valueerror() -> None:
    """F11: missing identity components raise HandicapLedgerReject."""
    with pytest.raises(HandicapLedgerReject, match="prediction_id components"):
        make_prediction_id(
            layer=L4_LAYER,
            forecast_label=FORECAST_MARKET_INFORMED_FAIR,
            game_id="",
            as_of_ts="2026-10-29T15:00:00Z",
            capture_id="cap",
            schema_version=LEDGER_SCHEMA_VERSION,
        )


def test_f13_commit_l1_stage_atomic_no_partial_write(tmp_path: Path) -> None:
    """F13: validate+dup-check all before any write."""
    store = AppendOnlyHandicapLedger(tmp_path / "f13.jsonl")
    ok = _l1_ok()
    dup = _l1_ok(factor="weather")  # same business identity
    with pytest.raises(HandicapLedgerReject, match="no writes"):
        commit_l1_stage(store, [ok, dup], decision_ts=DECISION_TS)
    assert len(store) == 0
    assert store.rows() == []
    commit_l1_stage(store, [ok], decision_ts=DECISION_TS)
    with pytest.raises(HandicapLedgerReject, match="no writes"):
        commit_l1_stage(store, [_l1_ok(delta=1.5)], decision_ts=DECISION_TS)
    assert len(store) == 1
