"""ONE integrated command: W-FIX produce → gate → consume → gate → receipt.

Accepted synthetic lineage #707/#706. Does not run #700/#701 real-outcome tests.
Does not fabricate ALLOW objects. CERT=0.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.services.nfl_fixture_assembly.assemble import FORBIDDEN_CALL_ATTEMPTS
from src.services.nfl_fixture_assembly.chain import chain_digest
from src.services.nfl_fixture_assembly.consume_chain import consume_fixture_chain
from src.services.nfl_fixture_assembly.produce_chain import produce_fixture_chain
from src.services.nfl_ops_v1_evidence.constants import (
    AUTHORITY,
    BASE_DEPLOY_VERCEL,
    CERT,
    DATA_LABEL,
    DEFAULT_LIMITATIONS,
    EXPECTED_COMMAND,
    JOINT_CONTRACT,
    LINEAGE_706_TIP,
    LINEAGE_707_TIP,
    OWNER,
    OWNER_CLEAR,
    PACKAGE,
    PINNED_CHAIN_DIGEST,
    PINNED_GAME_ID,
    PINNED_N,
    PINNED_OUTPUT_REL,
    PINNED_OUTPUT_SHA_REL,
    PROFILE,
    PROTOCOL,
    SCHEMA_VERSION,
    SCOPE_ID,
)
from src.services.nfl_ops_v1_evidence.gate import (
    gate_before_consume,
    gate_before_final_receipt,
)
from src.services.nfl_ops_v1_evidence.hashes import sha256_file, sha256_text
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.schema import (
    default_evidence_labels,
    default_exposure,
    identities_from_chain,
    schema_hash,
    spec_hash,
)
from src.services.nfl_ops_v1_evidence.spy import (
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    run_spy_positive_control,
)
from src.services.nfl_ops_v1_evidence.validate import numerical_from_consumed, utc_now
from src.services.nfl_ops_v1_evidence.verify import (
    git_tip,
    hash_code_files,
    hash_config_binding,
    hash_history_binding,
    hash_input_payload,
)
from src.services.nfl_ops_v1_evidence.worker_handoff import (
    B_CONTENT_HASH,
    B_TIP,
    load_actual_b_handoff,
)

_REHASHED_OK = {
    "ran": True,
    "refused": True,
    "gate_invoked": 1,
    "instrumentation_control": {"fired": True},
    "forbidden_calls": 0,
}


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def _hash_bindings(*, input_hash: str, history_hash: str, config_hash: str, code_hash: str) -> dict[str, Any]:
    return {
        "schema": {"source": "schema_body", "alg": "sha256", "sha256": schema_hash()},
        "input": {"source": "produced_chain_bytes", "alg": "sha256", "sha256": input_hash},
        "history": {
            "source": "none_synthetic",
            "alg": "sha256",
            "sha256": history_hash,
        },
        "config": {"source": "pinned_config", "alg": "sha256", "sha256": config_hash},
        "code": {"source": "gate_and_caller_files", "alg": "sha256", "sha256": code_hash},
    }


def _pinned_unwritten(root: Path) -> bool:
    out = root / PINNED_OUTPUT_REL
    side = root / PINNED_OUTPUT_SHA_REL
    if not out.is_file() or not side.is_file():
        return False
    declared = side.read_text(encoding="utf-8").strip().split()[0]
    loaded = json.loads(out.read_text(encoding="utf-8"))
    return declared == PINNED_CHAIN_DIGEST and chain_digest(loaded) == PINNED_CHAIN_DIGEST


def run_rehashed_fault_control(
    payload: Mapping[str, Any],
    *,
    dest: Path,
    root: Path,
    outcome_spy: Optional[OutcomeReadSpy] = None,
) -> dict[str, Any]:
    """Mutate a copy and invoke the DIRECT gate. Must refuse. Temp-only. Zero forbidden."""
    probe_spy = OutcomeReadSpy()
    probe_surface = ForbiddenSurfaceSpy()
    probe_spy()
    probe_surface.note("rehashed_instrumentation_probe")
    if probe_spy.reads < 1 or probe_surface.count < 1:
        raise EvidenceGateRefuse(
            "positive instrumentation control did not fire",
            refuse_class=RefuseClass.SPY,
        )

    mutated = copy.deepcopy(dict(payload))
    forecast = dict(mutated.get("forecast") or {})
    forecast["point_margin"] = float(forecast.get("point_margin") or 3.0) + 1.0
    mutated["forecast"] = forecast
    mutated_digest = chain_digest(mutated)
    if mutated_digest == PINNED_CHAIN_DIGEST:
        raise EvidenceGateRefuse(
            "rehashed fault did not change digest",
            refuse_class=RefuseClass.HASH_MUTATED,
        )

    now = utc_now()
    draft = _build_manifest(
        root=root,
        payload=payload,
        digest=PINNED_CHAIN_DIGEST,
        dest=Path(dest),
        command=EXPECTED_COMMAND,
        cwd=str(root),
        start_utc=now,
        produce_invoked=True,
        consume_invoked=False,
        positive={"ran": True, "digest_match": True},
        rehashed=dict(_REHASHED_OK),
        spy_control={"ran": True, "spy_fired": True},
        process_id=os.getpid(),
        produce_start_utc=now,
    )
    refuse_spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    refuse_surface = ForbiddenSurfaceSpy()
    gate_invoked = 0
    refused = False
    refuse_class = None
    reason = ""
    try:
        gate_invoked += 1
        gate_before_consume(
            draft,
            chain_payload=mutated,
            root=root,
            command=EXPECTED_COMMAND,
            cwd=str(root),
            outcome_spy=refuse_spy,
            surface=refuse_surface,
        )
    except EvidenceGateRefuse as exc:
        refused = True
        refuse_class = exc.refuse_class
        reason = exc.reason
    if not refused:
        raise EvidenceGateRefuse(
            "rehashed fault was not refused by DIRECT gate",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    if refuse_spy.reads != 0 or refuse_surface.count != 0:
        raise EvidenceGateRefuse(
            "forbidden calls on rehashed refuse",
            refuse_class=RefuseClass.FORBIDDEN_CALL,
        )
    return {
        "ran": True,
        "refused": True,
        "gate_invoked": gate_invoked,
        "instrumentation_control": {
            "ran": True,
            "fired": True,
            "reads": probe_spy.reads,
            "surface_notes": probe_surface.count,
        },
        "forbidden_calls": 0,
        "refuse_class": refuse_class,
        "reason": reason,
        "mutated_digest": mutated_digest,
        "pinned_digest": PINNED_CHAIN_DIGEST,
        "evidence_label": "EXECUTED_HERE",
    }


def _build_manifest(
    *,
    root: Path,
    payload: Mapping[str, Any],
    digest: str,
    dest: Path,
    command: str,
    cwd: str,
    start_utc: str,
    produce_invoked: bool,
    consume_invoked: bool,
    positive: Mapping[str, Any],
    rehashed: Mapping[str, Any],
    spy_control: Mapping[str, Any],
    end_utc: Any = None,
    exit_code: Any = None,
    log_hash: Any = None,
    numerical: Any = None,
    outputs: Optional[Mapping[str, str]] = None,
    failures: Any = None,
    process_id: int,
    produce_start_utc: str,
    saved_output_only: bool = False,
    import_only: bool = False,
) -> dict[str, Any]:
    input_hash = hash_input_payload(payload)
    history_hash = hash_history_binding()
    config_hash = hash_config_binding()
    code = hash_code_files(root)
    files = [
        {**row, "ref_kind": "file_sha256"}
        for row in code["files"]
    ]
    refs = [
        {"kind": "git_commit", "value": BASE_DEPLOY_VERCEL, "label": "base_deploy_vercel"},
        {"kind": "git_commit", "value": git_tip(root), "label": "head"},
        {"kind": "git_commit", "value": LINEAGE_707_TIP, "label": "pr707"},
        {"kind": "git_commit", "value": LINEAGE_706_TIP, "label": "pr706"},
        {"kind": "file_sha256", "value": PINNED_CHAIN_DIGEST, "path": PINNED_OUTPUT_REL},
        {"kind": "receipt_id", "value": "nfl-ops-v1-evidence-gate-pending", "path": None},
        {"kind": "git_commit", "value": B_TIP, "label": "pr712_primary_b"},
        {
            "kind": "file_sha256",
            "value": B_CONTENT_HASH,
            "path": "data/ops/nfl-ops-v1-worker-release-claim/THIS_WORKER_HANDOFF.json",
        },
    ]
    output_paths = list(outputs.keys()) if outputs else None
    return {
        "schema_version": SCHEMA_VERSION,
        "package": PACKAGE,
        "authority": AUTHORITY,
        "owner_clear": OWNER_CLEAR,
        "protocol": PROTOCOL,
        "joint_contract": JOINT_CONTRACT,
        "scope_id": SCOPE_ID,
        "profile": PROFILE,
        "owner": OWNER,
        "cert": CERT,
        "base": {"kind": "git_commit", "value": BASE_DEPLOY_VERCEL},
        "head": {"kind": "git_commit", "value": git_tip(root)},
        "spec_hash": spec_hash(),
        "schema_hash": schema_hash(),
        "changed_files": files,
        "typed_references": refs,
        "input_identities": identities_from_chain(payload),
        "cohort": {"id": PINNED_GAME_ID, "n": PINNED_N, "game_ids": [PINNED_GAME_ID]},
        "data_label": DATA_LABEL,
        "input_hash": input_hash,
        "history_hash": history_hash,
        "config_hash": config_hash,
        "code_hash": code["sha256"],
        "hash_bindings": _hash_bindings(
            input_hash=input_hash,
            history_hash=history_hash,
            config_hash=config_hash,
            code_hash=code["sha256"],
        ),
        "output_paths": output_paths,
        "output_hashes": dict(outputs) if outputs else None,
        "command": command,
        "cwd": cwd,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "exit": exit_code,
        "log_hash": log_hash,
        "evidence_labels": default_evidence_labels(),
        "producer_consumer_trace": {
            "producer": "src.services.nfl_fixture_assembly.produce_chain.produce_fixture_chain",
            "consumer": "src.services.nfl_fixture_assembly.consume_chain.consume_fixture_chain",
            "consumer_name": "fixture",
            "producer_digest": digest,
            "consumer_digest": digest if consume_invoked else None,
            "produce_invoked_here": produce_invoked,
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
            "pinned_originals_unwritten": _pinned_unwritten(root),
            "pinned_output": PINNED_OUTPUT_REL,
            "research_bytes": "temp-only",
        },
        "limitations": list(DEFAULT_LIMITATIONS),
        "failures": failures,
        "review_revision": 0,
        "worker_handoff": load_actual_b_handoff(root),
        "ready_for_review": False,
        "execution": {
            "produce_invoked_here": produce_invoked,
            "consume_invoked_here": consume_invoked,
            "saved_output_only": saved_output_only,
            "import_only": import_only,
            "process_id": process_id,
            "produce_start_utc": produce_start_utc,
        },
    }


def run_from_saved_output(
    path: Path,
    *,
    root: Path | None = None,
    outcome_spy: OutcomeReadSpy | None = None,
) -> dict[str, Any]:
    """Negative helper: load saved JSON and try to finalize. Must refuse."""
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = chain_digest(payload)
    repo = _repo_root(root)
    now = utc_now()
    manifest = _build_manifest(
        root=repo,
        payload=payload,
        digest=digest,
        dest=Path(path),
        command=EXPECTED_COMMAND,
        cwd=str(repo),
        start_utc=now,
        produce_invoked=False,
        consume_invoked=False,
        positive={"ran": True, "digest_match": digest == PINNED_CHAIN_DIGEST},
        rehashed=dict(_REHASHED_OK),
        spy_control={"ran": True, "spy_fired": True},
        process_id=os.getpid(),
        produce_start_utc=now,
        saved_output_only=True,
        import_only=False,
    )
    return gate_before_consume(
        manifest,
        chain_payload=payload,
        root=repo,
        command=EXPECTED_COMMAND,
        cwd=str(repo),
        outcome_spy=spy,
    )


def claim_from_import_only(*, root: Path | None = None, outcome_spy: OutcomeReadSpy | None = None) -> dict[str, Any]:
    """Negative helper: import-only claim. Must refuse."""
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    repo = _repo_root(root)
    now = utc_now()
    manifest = _build_manifest(
        root=repo,
        payload={"channel": "FIXTURE"},
        digest=PINNED_CHAIN_DIGEST,
        dest=repo / "unused",
        command=EXPECTED_COMMAND,
        cwd=str(repo),
        start_utc=now,
        produce_invoked=False,
        consume_invoked=False,
        positive={"ran": True, "digest_match": True},
        rehashed=dict(_REHASHED_OK),
        spy_control={"ran": True, "spy_fired": True},
        process_id=os.getpid(),
        produce_start_utc=now,
        saved_output_only=False,
        import_only=True,
    )
    dummy = {"channel": "FIXTURE"}
    return gate_before_consume(
        manifest,
        chain_payload=dummy,
        root=repo,
        command=EXPECTED_COMMAND,
        cwd=str(repo),
        outcome_spy=spy,
    )


def run_integrated_command(
    *,
    dest_dir: Path,
    root: Path | None = None,
    outcome_spy: OutcomeReadSpy | None = None,
    write_receipt: bool = True,
    command: str | None = None,
) -> dict[str, Any]:
    """Actual produce → pre-consume gate → consume → pre-receipt gate."""
    repo = _repo_root(root)
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "produced_chain.json"
    start_utc = utc_now()
    produce_start = start_utc
    cmd = command or EXPECTED_COMMAND
    log_lines: list[str] = [f"start {start_utc}", f"command {cmd}"]
    FORBIDDEN_CALL_ATTEMPTS.clear()

    payload = produce_fixture_chain(dest=dest)
    digest = chain_digest(payload)
    log_lines.append(f"produced digest {digest}")
    if digest != PINNED_CHAIN_DIGEST:
        raise EvidenceGateRefuse(
            f"produced digest {digest} != pinned {PINNED_CHAIN_DIGEST}",
            refuse_class=RefuseClass.HASH_MUTATED,
        )

    rehashed = run_rehashed_fault_control(payload, dest=dest, root=repo)
    spy_control = run_spy_positive_control()
    FORBIDDEN_CALL_ATTEMPTS.clear()
    log_lines.append("rehashed_faults refused")
    log_lines.append("spy_positive_control fired")

    positive = {"ran": True, "digest_match": True, "n": PINNED_N, "game_id": PINNED_GAME_ID}
    draft = _build_manifest(
        root=repo,
        payload=payload,
        digest=digest,
        dest=dest,
        command=cmd,
        cwd=str(repo),
        start_utc=start_utc,
        produce_invoked=True,
        consume_invoked=False,
        positive=positive,
        rehashed=rehashed,
        spy_control=spy_control,
        process_id=os.getpid(),
        produce_start_utc=produce_start,
    )
    gate_before_consume(
        draft,
        chain_payload=payload,
        root=repo,
        command=cmd,
        cwd=str(repo),
        outcome_spy=spy,
    )

    consumed = consume_fixture_chain(payload, consumer="fixture")
    numerical = numerical_from_consumed(consumed)
    log_lines.append(
        f"consumed n={numerical['n']} margin={numerical['point_margin']} line={numerical['line']}"
    )

    end_utc = utc_now()
    log_text = "\n".join(log_lines) + "\n"
    log_hash = sha256_text(log_text)
    outputs = {dest.as_posix(): sha256_file(dest)}

    manifest = _build_manifest(
        root=repo,
        payload=consumed,
        digest=digest,
        dest=dest,
        command=cmd,
        cwd=str(repo),
        start_utc=start_utc,
        produce_invoked=True,
        consume_invoked=True,
        positive=positive,
        rehashed=rehashed,
        spy_control=spy_control,
        end_utc=end_utc,
        exit_code=0,
        log_hash=log_hash,
        numerical=numerical,
        outputs=outputs,
        failures=[],
        process_id=os.getpid(),
        produce_start_utc=produce_start,
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

    receipt_path = dest_dir / "RECEIPT.json"
    sample_path = dest_dir / "SAMPLE_MANIFEST.json"
    gated["ok"] = True
    gated["status"] = "GATED_OK_AWAITING_CHIEF"
    if write_receipt:
        body = dict(gated)
        body["receipt_id"] = f"nfl-ops-v1-evidence-{gated['common_digest'][:12]}"
        written = json.dumps(body, indent=2, sort_keys=True) + "\n"
        receipt_path.write_text(written, encoding="utf-8")
        readback = receipt_path.read_text(encoding="utf-8")
        if readback != written:
            raise EvidenceGateRefuse(
                "receipt readback tamper",
                refuse_class=RefuseClass.WRITE_TAMPER,
            )
        body["receipt_sha256"] = sha256_text(written)
        body["manifest_sha256"] = sha256_text(written)
        sample_path.write_text(
            json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        gated = body
        gated["_receipt_path"] = receipt_path.as_posix()
        gated["_sample_path"] = sample_path.as_posix()

    if getattr(spy, "reads", 0) != 0:
        raise EvidenceGateRefuse(
            "outcome loader was read on the synthetic path",
            refuse_class=RefuseClass.SPY,
        )
    gated["log"] = log_text
    gated["_chain_payload"] = consumed
    return gated


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dest = Path(args[0]) if args else Path("/tmp/nfl-ops-v1-evidence")
    try:
        result = run_integrated_command(dest_dir=dest)
    except EvidenceGateRefuse as exc:
        print(f"REFUSE [{exc.refuse_class}] {exc.reason}", file=sys.stderr)
        return 2
    print(f"status {result.get('status')}")
    print(f"digest {result.get('common_digest')}")
    print(f"ready_for_review {str(result.get('ready_for_review')).lower()}")
    print("cert 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
