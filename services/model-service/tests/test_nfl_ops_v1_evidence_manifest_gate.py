"""NFL_OPS_V1 evidence-manifest gate tests. Synthetic only. CERT=0.

Does not run inherited #700/#701 real-outcome tests.
Does not fabricate ALLOW objects.
"""

from __future__ import annotations

import copy
import json
import math
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from src.services.nfl_fixture_assembly.assemble import FORBIDDEN_CALL_ATTEMPTS
from src.services.nfl_fixture_assembly.produce_chain import produce_fixture_chain
from src.services.nfl_hhl1_capture.identity import parse_utc
from src.services.nfl_ops_v1_evidence.constants import (
    PINNED_CHAIN_DIGEST,
    PINNED_GAME_ID,
    PINNED_OUTPUT_REL,
    PROFILE,
)
from src.services.nfl_ops_v1_evidence.gate import (
    assert_ready_for_review_allowed,
    gate_before_consume,
    gate_before_final_receipt,
    stamp_ready_for_review,
)
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.run import (
    _build_manifest,
    claim_from_import_only,
    run_from_saved_output,
    run_integrated_command,
    run_rehashed_fault_control,
)
from src.services.nfl_ops_v1_evidence.spy import OutcomeReadSpy, run_spy_positive_control
from src.services.nfl_ops_v1_evidence.validate import utc_now, validate_cutoff
from src.services.nfl_ops_v1_evidence.worker_handoff import (
    B_CONTENT_HASH,
    B_RELEASE_KIND,
    B_WORKER_ID,
    empty_worker_handoff_slot,
    load_actual_b_handoff,
    validate_worker_handoff,
)

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _reset_forbidden() -> Any:
    FORBIDDEN_CALL_ATTEMPTS.clear()
    yield
    FORBIDDEN_CALL_ATTEMPTS.clear()


@pytest.fixture
def produced(tmp_path: Path) -> tuple[dict[str, Any], Path]:
    dest = tmp_path / "chain.json"
    payload = produce_fixture_chain(dest=dest)
    return payload, dest


@pytest.fixture
def integrated(tmp_path: Path) -> dict[str, Any]:
    return run_integrated_command(dest_dir=tmp_path / "out", root=REPO)


def _pre_consume_draft(payload: dict[str, Any], dest: Path) -> dict[str, Any]:
    now = utc_now()
    return _build_manifest(
        root=REPO,
        payload=payload,
        digest=PINNED_CHAIN_DIGEST,
        dest=dest,
        command="pytest-pre-consume",
        cwd=str(REPO),
        start_utc=now,
        produce_invoked=True,
        consume_invoked=False,
        positive={"ran": True, "digest_match": True},
        rehashed={"ran": True, "refused": True},
        spy_control={"ran": True, "spy_fired": True},
        process_id=1,
        produce_start_utc=now,
    )


def _refuse_class(exc: EvidenceGateRefuse) -> str:
    return exc.refuse_class


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_positive_integrated_produce_consume_gate(integrated: dict[str, Any]) -> None:
    assert integrated["ok"] is True
    assert integrated["status"] == "GATED_OK_AWAITING_CHIEF"
    assert integrated["ready_for_review"] is False
    assert integrated["cert"] == 0
    assert integrated["common_digest"] == PINNED_CHAIN_DIGEST
    assert integrated["numerical_output"]["n"] == 1
    assert integrated["numerical_output"]["game_id"] == PINNED_GAME_ID
    assert integrated["numerical_output"]["point_margin"] == 3.0
    assert integrated["numerical_output"]["line"] == -3.0
    assert integrated["execution"]["produce_invoked_here"] is True
    assert integrated["execution"]["consume_invoked_here"] is True
    assert integrated["worker_handoff"]["content_hash"] == B_CONTENT_HASH
    assert integrated["worker_handoff"]["release_kind"] == B_RELEASE_KIND
    assert integrated["worker_handoff"]["not_a_pass"] is True
    assert integrated["worker_handoff"]["mocked_release"] is False
    assert integrated["worker_handoff"]["platform_capability"] == "ABSENT"
    assert integrated["worker_handoff"]["state"] == "QUIESCENT"
    assert integrated["worker_handoff"]["worker_id"] == B_WORKER_ID
    assert integrated["evidence_labels"]["produce_fixture_chain"] == "EXECUTED_HERE"
    assert integrated["evidence_labels"]["consume_fixture_chain"] == "EXECUTED_HERE"
    assert integrated["evidence_labels"]["inherited_real_outcome_tests"] == "NOT_RUN"
    assert integrated["evidence_labels"]["primary_b_worker_handoff"] == "SOURCE_INSPECTION"
    assert integrated["positive_control"]["digest_match"] is True
    assert integrated["rehashed_faults"]["refused"] is True
    assert integrated["spy_positive_control"]["spy_fired"] is True
    assert integrated["data_label"] == "SYNTHETIC"
    assert integrated["hash_bindings"]["input"]["source"] != "schema_body"
    assert integrated["input_hash"] != integrated["schema_hash"]


def test_positive_does_not_self_stamp_ready_for_review(integrated: dict[str, Any]) -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        stamp_ready_for_review(integrated, chief_verified=False, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.READY_FOR_REVIEW
    assert spy.reads == 0


def test_cli_exit_zero(tmp_path: Path) -> None:
    from src.services.nfl_ops_v1_evidence.run import main

    assert main([str(tmp_path / "cli")]) == 0


# ---------------------------------------------------------------------------
# Negative classes
# ---------------------------------------------------------------------------


def test_incomplete_missing_required_field(
    produced: tuple[dict[str, Any], Path],
) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    del draft["profile"]
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.INCOMPLETE
    assert spy.reads == 0


def test_stale_as_of_after_kickoff(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    mutated = copy.deepcopy(payload)
    mutated["cutoff"]["as_of_ts"] = "2026-11-08T18:00:01Z"
    mutated["provenance"]["as_of_ts"] = "2026-11-08T18:00:01Z"
    draft = _pre_consume_draft(payload, dest)
    draft["common_digest"] = PINNED_CHAIN_DIGEST
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=mutated, outcome_spy=spy)
    assert _refuse_class(exc.value) in {RefuseClass.STALE, RefuseClass.HASH_MUTATED}
    assert spy.reads == 0


def test_hash_mutated_content(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    mutated = copy.deepcopy(payload)
    mutated["forecast"]["point_margin"] = 99.0
    draft = _pre_consume_draft(payload, dest)
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=mutated, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.HASH_MUTATED
    assert spy.reads == 0


def test_wrong_profile(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["profile"] = "DEV_IF437"
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.WRONG_PROFILE_IDENTITY
    assert draft["profile"] != PROFILE
    assert spy.reads == 0


def test_wrong_identity_game_team_season_period(
    produced: tuple[dict[str, Any], Path],
) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["input_identities"]["game_id"] = "2024_01_KC_BUF"
    draft["input_identities"]["team"] = "KC"
    draft["input_identities"]["season"] = 2024
    draft["input_identities"]["period"] = "h1"
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.WRONG_PROFILE_IDENTITY
    assert spy.reads == 0


def test_wrong_count(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["cohort"]["n"] = 2
    draft["cohort"]["game_ids"] = [PINNED_GAME_ID, "extra"]
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.WRONG_COUNT
    assert spy.reads == 0


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, None, "3.0"])
def test_nonfinite_numerical(integrated: dict[str, Any], value: object) -> None:
    manifest = copy.deepcopy(integrated)
    manifest["numerical_output"]["point_margin"] = value
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_final_receipt(manifest, outcome_spy=spy)
    assert _refuse_class(exc.value) in {RefuseClass.NONFINITE, RefuseClass.TYPE}
    assert spy.reads == 0


def test_saved_output_only_refuses(tmp_path: Path) -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        run_from_saved_output(REPO / PINNED_OUTPUT_REL, root=REPO, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.SAVED_OUTPUT_ONLY
    assert spy.reads == 0


def test_import_only_refuses() -> None:
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        claim_from_import_only(root=REPO, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.IMPORT_ONLY
    assert spy.reads == 0


# ---------------------------------------------------------------------------
# Boundary coverage
# ---------------------------------------------------------------------------


def test_extra_top_level_key(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["unexpected_allow"] = {"result": "ALLOW_FIXTURE"}
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.EXTRA
    assert spy.reads == 0


@pytest.mark.parametrize("cert", [True, 0.0, "0", None])
def test_type_bool_null_cert(produced: tuple[dict[str, Any], Path], cert: object) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["cert"] = cert
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.TYPE
    assert spy.reads == 0


def test_cutoff_minus_equal_plus(produced: tuple[dict[str, Any], Path]) -> None:
    payload, _dest = produced
    cutoff = copy.deepcopy(payload["cutoff"])
    kickoff = parse_utc(cutoff["kickoff_ts"], field="kickoff_ts")
    expected = kickoff - timedelta(minutes=90)
    validate_cutoff(cutoff)

    minus = copy.deepcopy(cutoff)
    minus["decision_ts"] = (expected - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(EvidenceGateRefuse) as exc_minus:
        validate_cutoff(minus)
    assert _refuse_class(exc_minus.value) == RefuseClass.CUTOFF

    plus = copy.deepcopy(cutoff)
    plus["decision_ts"] = (expected + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(EvidenceGateRefuse) as exc_plus:
        validate_cutoff(plus)
    assert _refuse_class(exc_plus.value) == RefuseClass.CUTOFF

    as_of_plus = copy.deepcopy(cutoff)
    as_of_plus["as_of_ts"] = (kickoff + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(EvidenceGateRefuse) as exc_stale:
        validate_cutoff(as_of_plus)
    assert _refuse_class(exc_stale.value) == RefuseClass.STALE

    as_of_eq = copy.deepcopy(cutoff)
    as_of_eq["as_of_ts"] = kickoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    validate_cutoff(as_of_eq)


def test_unknown_freshness(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["input_identities"]["freshness"] = "UNKNOWN"
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.STALE
    assert spy.reads == 0


def test_unsupported_capability(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    mutated = copy.deepcopy(payload)
    mutated["capability"]["bits"] = ["JOINT_SCORE"]
    draft = _pre_consume_draft(payload, dest)
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=mutated, outcome_spy=spy)
    assert _refuse_class(exc.value) in {RefuseClass.CAPABILITY, RefuseClass.HASH_MUTATED}
    assert spy.reads == 0


def test_paired_arm_incomplete(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["producer_consumer_trace"]["consumer"] = ""
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) in {RefuseClass.PAIRED_ARM, RefuseClass.INCOMPLETE}
    assert spy.reads == 0


def test_malformed_channel_vs_absence(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    spy = OutcomeReadSpy()
    absent = copy.deepcopy(payload)
    del absent["channel"]
    with pytest.raises(EvidenceGateRefuse) as exc_abs:
        gate_before_consume(draft, chain_payload=absent, outcome_spy=spy)
    assert _refuse_class(exc_abs.value) in {RefuseClass.CHANNEL, RefuseClass.HASH_MUTATED}

    empty = copy.deepcopy(payload)
    empty["channel"] = ""
    with pytest.raises(EvidenceGateRefuse) as exc_empty:
        gate_before_consume(draft, chain_payload=empty, outcome_spy=spy)
    assert _refuse_class(exc_empty.value) in {RefuseClass.CHANNEL, RefuseClass.HASH_MUTATED}
    assert spy.reads == 0


def test_direct_api_consumer_cache_refused(
    produced: tuple[dict[str, Any], Path],
) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["producer_consumer_trace"]["consumer_name"] = "fair_lines_api"
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.CONSUMER
    assert spy.reads == 0


def test_real_mode_refuses_before_readers(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["data_label"] = "REAL"
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.REAL_MODE
    assert spy.reads == 0


def test_readback_tamper_and_partial_write(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    body = {"ok": True}
    written = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path.write_text(written, encoding="utf-8")
    path.write_text("{partial", encoding="utf-8")
    readback = path.read_text(encoding="utf-8")
    assert readback != written
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        raise EvidenceGateRefuse("receipt readback tamper", refuse_class=RefuseClass.WRITE_TAMPER)
    assert _refuse_class(exc.value) == RefuseClass.WRITE_TAMPER
    assert spy.reads == 0


def test_immutable_input_unproven(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["immutable_input_proof"]["pinned_originals_unwritten"] = False
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.WRITE_TAMPER
    assert spy.reads == 0


# ---------------------------------------------------------------------------
# Worker handoff slot + spy controls
# ---------------------------------------------------------------------------


def test_worker_handoff_binds_actual_b() -> None:
    handoff = load_actual_b_handoff(REPO)
    assert handoff["content_hash"] == B_CONTENT_HASH
    assert handoff["release_kind"] == B_RELEASE_KIND
    assert handoff["not_a_pass"] is True


def test_worker_handoff_slot_reserved_is_invented_substitute() -> None:
    with pytest.raises(EvidenceGateRefuse) as exc:
        validate_worker_handoff(empty_worker_handoff_slot())
    assert _refuse_class(exc.value) == RefuseClass.WORKER_HANDOFF


def test_worker_handoff_invented_pass_refused() -> None:
    slot = empty_worker_handoff_slot()
    slot["status"] = "RELEASE_CONFIRMED"
    with pytest.raises(EvidenceGateRefuse) as exc:
        validate_worker_handoff(slot)
    assert _refuse_class(exc.value) == RefuseClass.WORKER_HANDOFF


def test_worker_handoff_mocked_release_refused() -> None:
    slot = load_actual_b_handoff(REPO)
    slot["mocked_release"] = True
    with pytest.raises(EvidenceGateRefuse) as exc:
        validate_worker_handoff(slot)
    assert _refuse_class(exc.value) == RefuseClass.WORKER_HANDOFF


def test_worker_handoff_rewritten_not_a_pass_refused() -> None:
    slot = load_actual_b_handoff(REPO)
    slot["not_a_pass"] = False
    with pytest.raises(EvidenceGateRefuse) as exc:
        validate_worker_handoff(slot)
    assert _refuse_class(exc.value) == RefuseClass.WORKER_HANDOFF


def test_worker_handoff_invented_release_confirmed_refused() -> None:
    slot = load_actual_b_handoff(REPO)
    slot["state"] = "RELEASE_CONFIRMED"
    slot["release_kind"] = "PLATFORM_RELEASE_CONFIRMED"
    with pytest.raises(EvidenceGateRefuse) as exc:
        validate_worker_handoff(slot)
    assert _refuse_class(exc.value) == RefuseClass.WORKER_HANDOFF


def test_worker_handoff_hash_mutated_substitute_refused() -> None:
    slot = load_actual_b_handoff(REPO)
    slot["content_hash"] = "0" * 64
    with pytest.raises(EvidenceGateRefuse) as exc:
        validate_worker_handoff(slot)
    assert _refuse_class(exc.value) == RefuseClass.WORKER_HANDOFF


def test_spy_positive_control_fires() -> None:
    result = run_spy_positive_control()
    assert result["spy_fired"] is True
    assert result["refused"] is True
    assert result["forbidden_call_attempts"] >= 1


def test_rehashed_fault_control(produced: tuple[dict[str, Any], Path]) -> None:
    payload, _dest = produced
    result = run_rehashed_fault_control(payload)
    assert result["refused"] is True
    assert result["mutated_digest"] != PINNED_CHAIN_DIGEST


def test_schema_hash_cannot_substitute_input_hash(
    produced: tuple[dict[str, Any], Path],
) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["input_hash"] = draft["schema_hash"]
    draft["hash_bindings"]["input"]["sha256"] = draft["schema_hash"]
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.HASH_MUTATED
    assert spy.reads == 0


def test_bool_n_is_wrong_type(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    draft["cohort"]["n"] = True
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(draft, chain_payload=payload, outcome_spy=spy)
    assert _refuse_class(exc.value) == RefuseClass.TYPE
    assert spy.reads == 0


def test_chief_stamp_still_not_accepted(integrated: dict[str, Any]) -> None:
    stamped = stamp_ready_for_review(integrated, chief_verified=True)
    assert stamped["ready_for_review"] is True
    assert stamped["accepted"] is False
    assert stamped["cert"] == 0


def test_assert_ready_requires_full_gate(produced: tuple[dict[str, Any], Path]) -> None:
    payload, dest = produced
    draft = _pre_consume_draft(payload, dest)
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse):
        assert_ready_for_review_allowed(draft, chief_verified=True, outcome_spy=spy)
    assert spy.reads == 0
