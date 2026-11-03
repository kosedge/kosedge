"""R7_CORRECTNESS_V1 path on the shared evidence gate. CERT=0.

Does not replace the W-FIX pin checks. Dispatched only when profile is R7.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_hhl1_capture.identity import canonical_json, parse_utc, sha256_hex
from src.services.nfl_ops_v1_evidence.constants import (
    BASE_DEPLOY_VERCEL,
    CERT,
    DATA_LABEL,
    EVIDENCE_LABELS,
    JOINT_CONTRACT,
    PACKAGE,
    PROTOCOL,
    SCHEMA_VERSION,
    STAGE_PRE_RECEIPT,
)
from src.services.nfl_ops_v1_evidence.finite import require_bool, require_finite, require_int, require_str
from src.services.nfl_ops_v1_evidence.hashes import require_sha256_hex
from src.services.nfl_ops_v1_evidence.profiles import PROFILE_R7, R7_SCOPE_ID, require_active_profile
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.verify import VerificationContext, is_git_commit_sha
from src.services.nfl_r7_correctness_v1.pins import (
    CALENDAR_ID,
    EXPECTED_COMMAND,
    GATE_713_TIP,
    R6_A_TIP,
    R6_B_TIP,
)


def _refuse(refuse_class: str, reason: str, **detail: Any) -> None:
    raise EvidenceGateRefuse(reason, refuse_class=refuse_class, detail=detail)


def _as_map(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _refuse(RefuseClass.TYPE, f"{name} must be an object")
    return dict(value)


def build_r7_verification_context(
    *,
    root: Path,
    payload: Mapping[str, Any],
    command: str,
    cwd: str,
    config_hash: str,
    code_hash: str,
    history_hash: str,
    exit_code: Optional[int] = None,
    output_paths: Optional[list[Path | str]] = None,
    log_text: Optional[str] = None,
    git_head: str,
) -> VerificationContext:
    if not is_git_commit_sha(git_head):
        _refuse(RefuseClass.TYPE, f"git_head {git_head!r} is not a 40-hex commit")
    output_map: Optional[dict[str, bytes]] = None
    if output_paths is not None:
        output_map = {}
        for raw in output_paths:
            path = Path(raw)
            if not path.is_file():
                _refuse(RefuseClass.MISSING_CONTEXT, f"actual output file missing: {path}")
            output_map[path.as_posix()] = path.read_bytes()
    return VerificationContext(
        git_head=git_head,
        git_base=BASE_DEPLOY_VERCEL,
        source_revision=git_head,
        actual_input_hash=sha256_hex(canonical_json(dict(payload)).encode("utf-8")),
        actual_history_hash=history_hash,
        actual_config_hash=config_hash,
        actual_code_hash=code_hash,
        actual_command=command,
        actual_cwd=str(cwd),
        actual_exit=exit_code,
        output_bytes=output_map,
        log_bytes=None if log_text is None else log_text.encode("utf-8"),
    )


def validate_r7_manifest(
    manifest: Mapping[str, Any],
    *,
    stage: str,
    chain_payload: Optional[Mapping[str, Any]],
    verification: VerificationContext,
) -> dict[str, Any]:
    raw = dict(manifest)
    profile = require_active_profile(raw.get("profile"))
    if profile.profile_id != PROFILE_R7:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"validate_r7 got profile {profile.profile_id}",
        )
    if raw.get("schema_version") != SCHEMA_VERSION:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "schema_version mismatch")
    if raw.get("package") != PACKAGE:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "shared package mismatch")
    if raw.get("protocol") != PROTOCOL or raw.get("joint_contract") != JOINT_CONTRACT:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "shared protocol/joint mismatch")
    if raw.get("cert") != CERT:
        _refuse(RefuseClass.TYPE, "cert must stay 0")
    if raw.get("data_label") != DATA_LABEL:
        _refuse(RefuseClass.CHANNEL, "data_label must be SYNTHETIC")
    if raw.get("scope_id") != R7_SCOPE_ID:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "R7 scope_id mismatch")
    if raw.get("ready_for_review") is True:
        _refuse(RefuseClass.READY_FOR_REVIEW, "READY_FOR_REVIEW cannot be self-stamped")

    if not is_git_commit_sha(verification.git_head):
        _refuse(RefuseClass.TYPE, "verification git_head is not a 40-hex git commit")
    head = raw.get("head") or {}
    base = raw.get("base") or {}
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        _refuse(RefuseClass.TYPE, "base/head must be typed git_commit objects")
    if base.get("value") != BASE_DEPLOY_VERCEL:
        _refuse(RefuseClass.STALE, "base is not pinned deploy-vercel")
    if head.get("value") != verification.git_head:
        _refuse(RefuseClass.STALE, "head != actual git_head")

    for name in ("input_hash", "history_hash", "config_hash", "code_hash"):
        require_sha256_hex(raw.get(name), name)
    if raw.get("input_hash") != verification.actual_input_hash:
        _refuse(RefuseClass.HASH_MUTATED, "input_hash != actual payload bytes")
    if raw.get("history_hash") != verification.actual_history_hash:
        _refuse(RefuseClass.HASH_MUTATED, "history_hash != actual history bind")
    if raw.get("config_hash") != verification.actual_config_hash:
        _refuse(RefuseClass.HASH_MUTATED, "config_hash != actual R7 config bind")
    if raw.get("code_hash") != verification.actual_code_hash:
        _refuse(RefuseClass.HASH_MUTATED, "code_hash != actual R7 code bind")
    if chain_payload is None:
        _refuse(RefuseClass.MISSING_CONTEXT, "missing R7 produce payload")
    payload_hash = sha256_hex(canonical_json(dict(chain_payload)).encode("utf-8"))
    if payload_hash != verification.actual_input_hash:
        _refuse(RefuseClass.HASH_MUTATED, "supplied produce payload != actual input")
    if chain_payload.get("channel") != "SYNTHETIC":
        _refuse(RefuseClass.CHANNEL, "R7 payload channel must be SYNTHETIC")
    if chain_payload.get("real_mode_usable") is True:
        _refuse(RefuseClass.REAL_MODE, "real_mode_usable refused")

    rest = _as_map(chain_payload.get("rest_calendar") or raw.get("rest_calendar"), "rest_calendar")
    if rest.get("calendar_id") != CALENDAR_ID:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "REST_ACTUAL_ET_CALENDAR_V1 missing")
    if rest.get("used_production_rest_days_from_schedule") is not False:
        _refuse(RefuseClass.CHANNEL, "production rest helper is forbidden on R7")
    require_finite(rest.get("rest_days_home"), "rest_days_home")
    require_finite(rest.get("rest_days_away"), "rest_days_away")

    franchises = _as_map(
        chain_payload.get("franchise_bind") or raw.get("franchise_bind"),
        "franchise_bind",
    )
    require_str(franchises.get("franchise_key_home"), "franchise_key_home")
    require_str(franchises.get("franchise_key_away"), "franchise_key_away")
    if franchises.get("franchise_key_home") == franchises.get("franchise_key_away"):
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "home/away franchise collision")

    command = require_str(raw.get("command"), "command")
    if command != EXPECTED_COMMAND or verification.actual_command != EXPECTED_COMMAND:
        _refuse(RefuseClass.COMMAND, "R7 command mismatch")
    if require_str(raw.get("cwd"), "cwd") != verification.actual_cwd:
        _refuse(RefuseClass.STALE, "cwd != actual cwd")

    labels = _as_map(raw.get("evidence_labels"), "evidence_labels")
    for key, value in labels.items():
        if value not in EVIDENCE_LABELS:
            _refuse(RefuseClass.TYPE, f"evidence_labels.{key} unsupported")
    if labels.get("inherited_real_outcome_tests") != "NOT_RUN":
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "inherited real-outcome tests must stay NOT_RUN")

    trace = _as_map(raw.get("producer_consumer_trace"), "producer_consumer_trace")
    if trace.get("producer") != "r7_correctness_produce" or trace.get("consumer") != "r7_paired_recorder":
        _refuse(RefuseClass.PAIRED_ARM, "R7 paired producer/recorder missing")
    require_sha256_hex(trace.get("producer_digest"), "producer_digest")
    if stage == STAGE_PRE_RECEIPT:
        require_sha256_hex(trace.get("consumer_digest"), "consumer_digest")
        if trace.get("consumer_digest") != trace.get("producer_digest"):
            _refuse(RefuseClass.PAIRED_ARM, "consumer_digest != producer_digest")

    refs = raw.get("typed_references")
    if not isinstance(refs, list) or not refs:
        _refuse(RefuseClass.INCOMPLETE, "typed_references missing")
    wanted = {R6_A_TIP, R6_B_TIP, GATE_713_TIP}
    seen = {str(row.get("value")) for row in refs if isinstance(row, Mapping)}
    if not wanted.issubset(seen):
        _refuse(RefuseClass.INCOMPLETE, "typed_references missing R6 A/B or #713 tip")

    exposure = _as_map(raw.get("exposure"), "exposure")
    for key in (
        "subscriber_consumable",
        "betting_consumable",
        "production_consumable",
        "env_bypass_honored",
        "cacheable",
    ):
        if exposure.get(key) is not False:
            _refuse(RefuseClass.CONSUMER, f"exposure.{key} must be false")

    if stage == STAGE_PRE_RECEIPT:
        if verification.actual_exit != 0 or raw.get("exit") != 0:
            _refuse(RefuseClass.EXIT, "R7 exit must be 0")
        numerical = _as_map(raw.get("numerical_output"), "numerical_output")
        require_finite(numerical.get("if_margin"), "if_margin")
        require_finite(numerical.get("q2_margin"), "q2_margin")
        require_finite(numerical.get("c_margin"), "c_margin")
        if numerical.get("game_id") != "SYNTHETIC_2018_W06_LAC_LAR":
            _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "unexpected R7 game_id")
        require_bool(raw.get("ok") if "ok" in raw else True, "ok")
        if verification.log_bytes is None:
            _refuse(RefuseClass.MISSING_CONTEXT, "verification log bytes missing")
        if sha256_hex(verification.log_bytes) != raw.get("log_hash"):
            _refuse(RefuseClass.HASH_MUTATED, "log_hash != actual log bytes")
        parse_utc(raw.get("start_utc"), field="start_utc")
        parse_utc(raw.get("end_utc"), field="end_utc")
        if not isinstance(raw.get("failures"), list):
            _refuse(RefuseClass.TYPE, "failures must be a list")
    return raw
