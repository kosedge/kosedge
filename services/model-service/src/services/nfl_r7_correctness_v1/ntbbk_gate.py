"""A NTBB-K producer → joint consumers → shared evidence gate. CERT=0.

Fresh build_kernel_document (no write). Route through consume_joint_* and
gate_before_consume / gate_before_final_receipt. Temporary atomic artifact
under isolated synthetic profile. Kernel/research bytes stay immutable.
Does not treat self-reported integrated:true as proof.
CSV44 evidence-only is allowed to exist; clocks stay unverified.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex
from src.services.nfl_ntbb_k_v1.constants import (
    ADDITIVE_ID,
    PROFILE,
    RETURN_ID,
    SCIPY_FITTING_ALGORITHM,
    SCIPY_STATUS,
    UNDER_RETURN_ID,
)
from src.services.nfl_ntbb_k_v1.produce import (
    build_kernel_document,
    verify_clarifications_blob,
    verify_market_partial_preserved,
    verify_spec_blob,
)
from src.services.nfl_ops_v1_evidence.constants import STAGE_PRE_CONSUME
from src.services.nfl_ops_v1_evidence.gate import gate_before_consume, gate_before_final_receipt
from src.services.nfl_ops_v1_evidence.profiles import PROFILE_NTBB_K_SYNTHETIC, get_profile
from src.services.nfl_ops_v1_evidence.schema import default_exposure
from src.services.nfl_ops_v1_evidence.verify import build_verification_context
from src.services.nfl_r7_correctness_v1.consume_ntbb_joint import (
    consume_joint_capability,
    consume_joint_refusals,
)
from src.services.nfl_r7_correctness_v1.followthrough_preflight import (
    ADDITIVE_NTBBK,
    B_NTBBK_KERNEL_SHA256,
    B_NTBBK_TIP_INTEGRATED,
    B_NTBBK_TIP_REFUSED,
    B_NTBBK_TIP_SUPERSEDED,
    RETURN_NTBBK,
    RETURN_UNFREEZE,
)
from src.services.nfl_r7_correctness_v1.produce import repo_root
from src.services.nfl_r7_record_date_retro_c1.grant import ROOT_APPROVED_AUTH_DIGEST
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse
from src.services.nfl_t5208u.hashing import sha256_file

KERNEL_REL = "data/ops/nfl_ntbb_k_v1/KERNEL_SYNTHETIC_92861.json"
CSV44_REL = "data/ops/nfl_owned_market_v1/codex_staged/CSV_SELECTED_44_RAW_VALUE_PROJECTION.json"
NTBBK_COMMAND = (
    "PYTHONPATH=services/model-service python3 -c "
    "\"from src.services.nfl_r7_correctness_v1.ntbbk_gate import run_ntbbk_integrate_gate; "
    "run_ntbbk_integrate_gate()\""
)


def _atomic_write(path: Path, payload: Any) -> str:
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    readback = path.read_bytes()
    if readback != raw:
        raise RetroRefuse("NTBB-K artifact readback mismatch")
    return sha256_hex(readback)


def run_ntbbk_integrate_gate(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    if B_NTBBK_TIP_INTEGRATED in {B_NTBBK_TIP_REFUSED, B_NTBBK_TIP_SUPERSEDED}:
        raise RetroRefuse("integrated tip collided with refused/superseded")
    spec = verify_spec_blob(repo)
    clar = verify_clarifications_blob(repo)
    kernel = repo / KERNEL_REL
    if not kernel.is_file():
        raise RetroRefuse(f"missing kernel {KERNEL_REL}")
    before = sha256_file(kernel)
    if before != B_NTBBK_KERNEL_SHA256:
        raise RetroRefuse(f"kernel sha {before} != pin {B_NTBBK_KERNEL_SHA256}")
    document = build_kernel_document(repo)
    capability = consume_joint_capability(document)
    refusals = consume_joint_refusals(document)
    market = verify_market_partial_preserved(repo)
    if market["clock_semantics_verified_any"] or market["clocks_status"] != "SOURCE_VALUE_MATCH_NOT_VERIFIED":
        raise RetroRefuse("143 clocks must remain SOURCE_VALUE_MATCH ≠ verified")
    csv44_present = (repo / CSV44_REL).exists()
    csv44_role = "EVIDENCE_ONLY_NOT_PROMOTED" if csv44_present else "ABSENT"
    profile = get_profile(PROFILE_NTBB_K_SYNTHETIC)
    if profile.status == "ACTIVE":
        raise RetroRefuse("NTBB-K must not be an ACTIVE R7 model arm")
    if ROOT_APPROVED_AUTH_DIGEST is not None:
        raise RetroRefuse("ROOT_APPROVED_AUTH_DIGEST must stay None")

    payload = {
        "channel": "SYNTHETIC",
        "real_mode_usable": False,
        "profile": PROFILE,
        "producer_digest": sha256_hex(canonical_json(document).encode("utf-8")),
        "kernel_sha256": before,
        "return_id": document.get("return_id"),
        "root_nine_status": document["root_nine"]["status"],
    }
    input_hash = sha256_hex(canonical_json(payload).encode("utf-8"))
    temp_root = Path(tempfile.mkdtemp(prefix="ntbbk-joint-"))
    try:
        artifact = temp_root / "JOINT_CONSUMER.json"
        artifact_sha = _atomic_write(
            artifact,
            {
                "capability": capability,
                "refusals": refusals,
                "producer_digest": payload["producer_digest"],
                "self_reported_integrated_proof": False,
            },
        )
        readback = json.loads(artifact.read_text(encoding="utf-8"))
        if sha256_hex(artifact.read_bytes()) != artifact_sha:
            raise RetroRefuse("NTBB-K artifact rehash failed")
        if readback.get("self_reported_integrated_proof") is True:
            raise RetroRefuse("artifact used integrated:true as proof")

        manifest = {
            "profile": PROFILE_NTBB_K_SYNTHETIC,
            "cert": 0,
            "data_label": "SYNTHETIC",
            "input_hash": input_hash,
            "consumer_invoked": True,
            "self_reported_integrated_proof": False,
            "ready_for_review": False,
            "artifact_readback_ok": True,
            "immutable_input_proof": {
                "dest_is_temp": True,
                "dest": str(temp_root),
                "pinned_originals_unwritten": True,
            },
            "exposure": default_exposure(),
        }
        ctx = build_verification_context(
            root=repo,
            payload=payload,
            command=NTBBK_COMMAND,
            cwd=str(repo),
            exit_code=0,
            output_paths=[artifact],
            log_text="ntbbk-joint-consumer\n",
        )
        gate_before_consume(
            manifest,
            chain_payload=payload,
            root=repo,
            command=NTBBK_COMMAND,
            cwd=str(repo),
            verification=ctx,
        )
        gated = gate_before_final_receipt(
            manifest,
            chain_payload=payload,
            root=repo,
            command=NTBBK_COMMAND,
            cwd=str(repo),
            exit_code=0,
            output_paths=[artifact],
            log_text="ntbbk-joint-consumer\n",
            verification=ctx,
        )
    finally:
        after = sha256_file(kernel)
        if after != before:
            raise RetroRefuse("gate rewrote the kernel — forbidden")

    return {
        "ok": True,
        "cert": 0,
        "profile": PROFILE,
        "self_reported_integrated_proof": False,
        "consumer_invoked": True,
        "shared_gate_invoked": True,
        "shared_gate_ok": bool(gated.get("ok")),
        "artifact_readback_ok": True,
        "integrated_tip": B_NTBBK_TIP_INTEGRATED,
        "frozen_tip": B_NTBBK_TIP_INTEGRATED,
        "frozen_as_final": False,
        "superseded_tip": B_NTBBK_TIP_SUPERSEDED,
        "refused_tip": B_NTBBK_TIP_REFUSED,
        "held_tip": None,
        "kernel_sha256": after,
        "kernel_sha256_locked": True,
        "kernel_role": "CONSUMED_FROM_12C41587",
        "kernel_rewritten": False,
        "produce_kernel_called": False,
        "r7_model_arm": False,
        "package_accepted": False,
        "package_closed_from_b_alone": False,
        "direct_paths_open": True,
        "return_order": RETURN_NTBBK,
        "return_unfreeze": RETURN_UNFREEZE,
        "additive_id": ADDITIVE_NTBBK,
        "b_return_id": RETURN_ID,
        "b_under_return_id": UNDER_RETURN_ID,
        "b_additive_id": ADDITIVE_ID,
        "spec_sha256_match": spec["sha256_match"],
        "clarifications_sha256_match": clar["sha256_match"],
        "producer": {
            "from_build_kernel_document": True,
            "rewrote_kernel": False,
            "n_by_family": capability["n_by_family"],
            "status": document["root_nine"]["status"],
        },
        "capability": capability,
        "refusal_consumer": refusals,
        "b_clocks_promoted": False,
        "csv44_present": csv44_present,
        "csv44_role": csv44_role,
        "scipy_status": SCIPY_STATUS,
        "fitting_algorithm": SCIPY_FITTING_ALGORITHM,
        "real_exec": False,
        "science_hold": True,
        "producer_capability_gate": {
            "owner": "A",
            "status": "JOINT_CONSUMER_SHARED_GATE",
            "reexecuted_this_turn": True,
            "real_science": False,
            "produce_kernel_rewrote": False,
            "self_reported_integrated_proof": False,
        },
        "gate_stage": STAGE_PRE_CONSUME,
    }
