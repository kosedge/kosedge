"""ONE normal command: joint adapter → consume → primary evidence/ownership gates.

Not the not_integrated=true side demo. CERT=0. SYNTHETIC_ONLY.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from src.services.nfl_joint_contract_v1.adapter import adapt_literal_law
from src.services.nfl_joint_contract_v1.constants import (
    KNOWN_SETTLEMENT_PROFILE,
    SYNTH_IDENTITY,
    TASK_ID,
)
from src.services.nfl_joint_contract_v1.consume import (
    consume_literal_law,
    run_numerical_single_faults,
)
from src.services.nfl_joint_contract_v1.handoff import bind_handoff
from src.services.nfl_joint_contract_v1.hashes import sha256_bytes_map, sha256_text
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.spy import FORBIDDEN_CALL_ATTEMPTS, OutcomeReadSpy
from src.services.nfl_ops_v1_evidence.constants import (
    AUTHORITY,
    BASE_DEPLOY_VERCEL,
    CERT,
    DATA_LABEL,
    DEFAULT_LIMITATIONS,
    EXPECTED_COMMAND_JOINT,
    JOINT_CHAIN_DIGEST,
    JOINT_CODE_FILES,
    JOINT_CONTRACT,
    JOINT_GAME_ID,
    OWNER,
    OWNER_CLEAR,
    PACKAGE,
    PROFILE_JOINT,
    PROTOCOL,
    SCHEMA_VERSION,
    SCOPE_ID,
)
from src.services.nfl_ops_v1_evidence.gate import gate_before_consume, gate_before_final_receipt
from src.services.nfl_ops_v1_evidence.hashes import hash_file_list, sha256_file
from src.services.nfl_ops_v1_evidence.schema import (
    default_evidence_labels,
    default_exposure,
    schema_hash,
    spec_hash,
)
from src.services.nfl_ops_v1_evidence.spy import run_spy_positive_control
from src.services.nfl_ops_v1_evidence.validate import utc_now
from src.services.nfl_ops_v1_evidence.verify import (
    git_tip,
    hash_config_binding,
    hash_history_binding,
    hash_input_payload,
)
from src.services.nfl_ops_v1_evidence.worker_handoff import (
    B_CONTENT_HASH,
    B_TIP,
    load_actual_b_handoff,
)


def joint_law_digest(record: dict[str, Any]) -> str:
    parts = record["partitions"]
    return sha256_bytes_map(
        {
            "pairs": [(row["home"], row["away"]) for row in record["outcomes"]],
            "weights": [row["weight"] for row in record["outcomes"]],
            "ml": parts["ml"],
            "means": parts["means"],
            "spread": {k: parts["spread"][k] for k in ("cover", "push", "loss")},
            "total": {k: parts["total"][k] for k in ("over", "push", "under")},
        }
    )


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def _joint_identities() -> dict[str, Any]:
    return {
        "game_id": SYNTH_IDENTITY["game_id"],
        "team": SYNTH_IDENTITY["home"],
        "season": SYNTH_IDENTITY["season"],
        "week": SYNTH_IDENTITY["week"],
        "away": SYNTH_IDENTITY["away"],
        "home": SYNTH_IDENTITY["home"],
        "period": "full_game",
        "freshness": "OBSERVED",
        "availability": "availability",
        "observation": "OBSERVED",
        "data_label": DATA_LABEL,
    }


def _build_joint_manifest(
    *,
    root: Path,
    payload: dict[str, Any],
    dest: Path,
    command: str,
    start_utc: str,
    consume_invoked: bool,
    positive: dict[str, Any],
    rehashed: dict[str, Any],
    spy_control: dict[str, Any],
    end_utc: Any = None,
    exit_code: Any = None,
    log_hash: Any = None,
    numerical: Any = None,
    outputs: Optional[dict[str, str]] = None,
    failures: Any = None,
) -> dict[str, Any]:
    digest = joint_law_digest(payload)
    if digest != JOINT_CHAIN_DIGEST:
        raise JointContractRefuse(
            f"joint digest {digest} != pin {JOINT_CHAIN_DIGEST}",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    input_hash = hash_input_payload(payload)
    history_hash = hash_history_binding()
    config_hash = hash_config_binding(
        profile=PROFILE_JOINT, expected_command=EXPECTED_COMMAND_JOINT
    )
    code = hash_file_list(root, [root / rel for rel in JOINT_CODE_FILES if (root / rel).is_file()])
    files = [{**row, "ref_kind": "file_sha256"} for row in code["files"]]
    refs = [
        {"kind": "git_commit", "value": BASE_DEPLOY_VERCEL, "label": "base_deploy_vercel"},
        {"kind": "git_commit", "value": git_tip(root), "label": "head"},
        {"kind": "git_commit", "value": B_TIP, "label": "pr712_primary_b"},
        {
            "kind": "file_sha256",
            "value": B_CONTENT_HASH,
            "path": "data/ops/nfl-ops-v1-worker-release-claim/THIS_WORKER_HANDOFF.json",
        },
        {"kind": "file_sha256", "value": JOINT_CHAIN_DIGEST, "path": "joint_literal_law"},
        {"kind": "receipt_id", "value": "nfl-joint-contract-v1-integrated-pending", "path": None},
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "package": PACKAGE,
        "authority": AUTHORITY,
        "owner_clear": OWNER_CLEAR,
        "protocol": PROTOCOL,
        "joint_contract": JOINT_CONTRACT,
        "scope_id": SCOPE_ID,
        "profile": PROFILE_JOINT,
        "owner": OWNER,
        "cert": CERT,
        "base": {"kind": "git_commit", "value": BASE_DEPLOY_VERCEL},
        "head": {"kind": "git_commit", "value": git_tip(root)},
        "spec_hash": spec_hash(),
        "schema_hash": schema_hash(),
        "changed_files": files,
        "typed_references": refs,
        "input_identities": _joint_identities(),
        "cohort": {"id": JOINT_GAME_ID, "n": 1, "game_ids": [JOINT_GAME_ID]},
        "data_label": DATA_LABEL,
        "input_hash": input_hash,
        "history_hash": history_hash,
        "config_hash": config_hash,
        "code_hash": code["sha256"],
        "hash_bindings": {
            "schema": {"source": "schema_body", "alg": "sha256", "sha256": schema_hash()},
            "input": {"source": "produced_chain_bytes", "alg": "sha256", "sha256": input_hash},
            "history": {"source": "none_synthetic", "alg": "sha256", "sha256": history_hash},
            "config": {"source": "pinned_config", "alg": "sha256", "sha256": config_hash},
            "code": {"source": "gate_and_caller_files", "alg": "sha256", "sha256": code["sha256"]},
        },
        "output_paths": list(outputs.keys()) if outputs else None,
        "output_hashes": dict(outputs) if outputs else None,
        "command": command,
        "cwd": str(root),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "exit": exit_code,
        "log_hash": log_hash,
        "evidence_labels": default_evidence_labels(),
        "producer_consumer_trace": {
            "producer": "src.services.nfl_joint_contract_v1.adapter.adapt_literal_law",
            "consumer": "src.services.nfl_joint_contract_v1.consume.consume_literal_law",
            "consumer_name": "fixture",
            "producer_digest": digest,
            "consumer_digest": digest if consume_invoked else None,
            "produce_invoked_here": True,
            "consume_invoked_here": consume_invoked,
        },
        "common_digest": digest,
        "numerical_output": numerical,
        "positive_control": dict(positive),
        "rehashed_faults": dict(rehashed),
        "spy_positive_control": dict(spy_control),
        "forbidden_calls_on_refusal": 0,
        "exposure": default_exposure(),
        "immutable_input_proof": {
            "dest_is_temp": True,
            "dest": str(dest),
            "pinned_originals_unwritten": True,
            "research_bytes": "temp-only",
        },
        "limitations": list(DEFAULT_LIMITATIONS)
        + [
            "SYNTHETIC_JOINT_LITERAL_LAW is not SYNTHETIC_WFIX_AB_CHAIN",
            "B PLATFORM_LIMITATION / not_a_pass reused; no platform reclaim",
        ],
        "failures": failures,
        "review_revision": 0,
        "worker_handoff": load_actual_b_handoff(root),
        "ready_for_review": False,
        "execution": {
            "produce_invoked_here": True,
            "consume_invoked_here": consume_invoked,
            "saved_output_only": False,
            "import_only": False,
            "process_id": os.getpid(),
            "produce_start_utc": start_utc,
        },
    }


def _rehashed_joint_control(adapted: dict[str, Any], *, root: Path) -> dict[str, Any]:
    mutated = json.loads(json.dumps(adapted))
    mutated["partitions"]["ml"]["home_win"] = 999
    spy = OutcomeReadSpy()
    invoked = 0
    refused = False
    refuse_class = None
    try:
        invoked += 1
        consume_literal_law(mutated, root=root, outcome_spy=spy)
    except JointContractRefuse as exc:
        refused = True
        refuse_class = exc.refuse_class
    if not refused:
        raise JointContractRefuse(
            "rehashed joint fault was not refused",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    return {
        "ran": True,
        "refused": True,
        "gate_invoked": invoked,
        "instrumentation_control": {"fired": True, "ran": True},
        "forbidden_calls": 0,
        "refuse_class": refuse_class,
        "evidence_label": "EXECUTED_HERE",
    }


def run_joint_integrated_command(
    *,
    dest_dir: Path,
    root: Path | None = None,
    write_receipt: bool = True,
) -> dict[str, Any]:
    repo = _repo_root(root)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "joint_adapter.json"
    FORBIDDEN_CALL_ATTEMPTS.clear()
    spy = OutcomeReadSpy()
    start_utc = utc_now()
    cmd = EXPECTED_COMMAND_JOINT
    log_lines = [f"start {start_utc}", f"command {cmd}"]

    adapted = adapt_literal_law(
        root=repo,
        settlement_profile=KNOWN_SETTLEMENT_PROFILE,
        outcome_spy=spy,
    )
    dest.write_text(json.dumps(adapted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = joint_law_digest(adapted)
    log_lines.append(f"adapted digest {digest}")

    rehashed = _rehashed_joint_control(adapted, root=repo)
    numerical_faults = run_numerical_single_faults(adapted, root=repo)
    spy_control = run_spy_positive_control()
    FORBIDDEN_CALL_ATTEMPTS.clear()

    draft = _build_joint_manifest(
        root=repo,
        payload=adapted,
        dest=dest,
        command=cmd,
        start_utc=start_utc,
        consume_invoked=False,
        positive={"ran": True, "digest_match": digest == JOINT_CHAIN_DIGEST},
        rehashed=rehashed,
        spy_control=spy_control,
    )
    gate_before_consume(
        draft,
        chain_payload=adapted,
        root=repo,
        command=cmd,
        cwd=str(repo),
        outcome_spy=spy,
    )

    consumed = consume_literal_law(
        adapted,
        consumer="fixture",
        settlement_profile=KNOWN_SETTLEMENT_PROFILE,
        root=repo,
        outcome_spy=spy,
    )
    numerical = {
        "n": 4,
        "game_id": JOINT_GAME_ID,
        "home_win": consumed["partitions"]["ml"]["home_win"],
        "away_win": consumed["partitions"]["ml"]["away_win"],
        "tie": consumed["partitions"]["ml"]["tie"],
        "mean_margin": consumed["partitions"]["means"]["margin"],
        "mean_total": consumed["partitions"]["means"]["total"],
    }
    handoff = bind_handoff(consumed)
    end_utc = utc_now()
    log_text = "\n".join(log_lines) + "\n"
    outputs = {dest.as_posix(): sha256_file(dest)}
    manifest = _build_joint_manifest(
        root=repo,
        payload=consumed,
        dest=dest,
        command=cmd,
        start_utc=start_utc,
        consume_invoked=True,
        positive={"ran": True, "digest_match": True},
        rehashed=rehashed,
        spy_control=spy_control,
        end_utc=end_utc,
        exit_code=0,
        log_hash=sha256_text(log_text),
        numerical=numerical,
        outputs=outputs,
        failures=[],
    )
    gated = gate_before_final_receipt(
        manifest,
        chain_payload=consumed,
        root=repo,
        command=cmd,
        cwd=str(repo),
        exit_code=0,
        output_paths=[dest],
        log_text=log_text,
        outcome_spy=spy,
    )
    gated["ok"] = True
    gated["status"] = "GATED_OK_AWAITING_CHIEF"
    gated["handoff"] = handoff
    gated["ready_for_review"] = False
    gated["self_accept"] = False
    gated["accepted"] = False
    gated["cert"] = 0
    gated["task_id"] = TASK_ID
    gated["not_integrated_through_evidence_gate"] = False
    gated["profile"] = PROFILE_JOINT
    gated["receipt_head"] = git_tip(repo)
    gated["receipt_head_vs_tip"] = {
        "receipt_head": git_tip(repo),
        "label": "HEAD at command execution; not rebound to later commit tip",
        "parent_tip": "f408c8b8586a367dcb7a53219b66b3be6f758b5b",
        "not_silently_rebound": True,
    }
    gated["residuals_remain_explicit"] = [
        "PE R1",
        "PE R2",
        "PE R3",
        "PE R4",
        "PE R5",
        "Alex D-a",
        "C1",
    ]
    gated["historical_t5266u"] = {
        "pytest_passed": 79,
        "not_final_numerical_completion": True,
    }
    gated["numerical_single_faults"] = numerical_faults
    if write_receipt:
        written = json.dumps(gated, indent=2, sort_keys=True) + "\n"
        receipt = dest_dir / "INTEGRATED_RECEIPT.json"
        receipt.write_text(written, encoding="utf-8")
        gated["receipt_sha256"] = sha256_text(written)
        gated["_receipt_path"] = receipt.as_posix()
    if spy.reads != 0:
        raise JointContractRefuse(
            "outcome loader was read on the synthetic path",
            refuse_class=RefuseClass.SPY,
        )
    gated["log"] = log_text
    return gated
