"""Isolated NTBB_K_SYNTHETIC_KERNEL_V1 path on the shared evidence gate. CERT=0.

REGISTERED isolated profile — not an ACTIVE R7 model arm.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex
from src.services.nfl_ops_v1_evidence.profiles import PROFILE_NTBB_K_SYNTHETIC, get_profile
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.verify import VerificationContext
from src.services.nfl_ops_v1_evidence.constants import STAGE_PRE_RECEIPT


def _refuse(refuse_class: str, reason: str, **detail: Any) -> None:
    raise EvidenceGateRefuse(reason, refuse_class=refuse_class, detail=detail)


def validate_ntbbk_manifest(
    raw: Mapping[str, Any],
    *,
    stage: str,
    chain_payload: Mapping[str, Any] | None,
    verification: VerificationContext,
) -> dict[str, Any]:
    profile = get_profile(PROFILE_NTBB_K_SYNTHETIC)
    if raw.get("profile") != PROFILE_NTBB_K_SYNTHETIC:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "NTBB-K profile mismatch")
    if profile.status == "ACTIVE":
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, "NTBB-K must not be an ACTIVE R7 arm")
    if raw.get("cert") != 0:
        _refuse(RefuseClass.TYPE, "NTBB-K cert must be 0")
    if raw.get("data_label") != "SYNTHETIC":
        _refuse(RefuseClass.REAL_MODE, "NTBB-K data_label must be SYNTHETIC")
    if raw.get("ready_for_review") is True:
        _refuse(RefuseClass.READY_FOR_REVIEW, "NTBB-K cannot self-stamp READY_FOR_REVIEW")
    if raw.get("self_reported_integrated_proof") is True:
        _refuse(RefuseClass.SAVED_OUTPUT_ONLY, "self-reported integrated:true is not proof")
    if chain_payload is None:
        _refuse(RefuseClass.MISSING_CONTEXT, "missing NTBB-K producer payload")
    if chain_payload.get("channel") != "SYNTHETIC":
        _refuse(RefuseClass.CHANNEL, "NTBB-K payload channel must be SYNTHETIC")
    if chain_payload.get("real_mode_usable") is True:
        _refuse(RefuseClass.REAL_MODE, "real_mode_usable refused")
    payload_hash = sha256_hex(canonical_json(dict(chain_payload)).encode("utf-8"))
    if payload_hash != verification.actual_input_hash:
        _refuse(RefuseClass.HASH_MUTATED, "NTBB-K payload != actual input")
    if raw.get("input_hash") != payload_hash:
        _refuse(RefuseClass.HASH_MUTATED, "NTBB-K input_hash != payload")
    if raw.get("consumer_invoked") is not True:
        _refuse(RefuseClass.SAVED_OUTPUT_ONLY, "joint consumer was not invoked")
    dest = str((raw.get("immutable_input_proof") or {}).get("dest") or "")
    if not dest:
        _refuse(RefuseClass.WRITE_TAMPER, "NTBB-K dest missing")
    resolved = Path(dest).resolve()
    try:
        resolved.relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError:
        _refuse(RefuseClass.WRITE_TAMPER, "NTBB-K dest must be temporary")
    exposure = dict(raw.get("exposure") or {})
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
        if raw.get("artifact_readback_ok") is not True:
            _refuse(RefuseClass.WRITE_TAMPER, "NTBB-K artifact readback missing")
        if verification.actual_exit is None:
            _refuse(RefuseClass.MISSING_CONTEXT, "observed process exit missing")
        out = dict(raw)
        out["ok"] = True
        return out
    return dict(raw)
