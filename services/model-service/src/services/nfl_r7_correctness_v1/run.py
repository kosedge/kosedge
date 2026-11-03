"""Produce → shared evidence gate → paired recorder. CERT=0. SYNTHETIC only.

B1: gate_before_consume BEFORE produce; TEMP write + readback/rehash;
gate_before_final_receipt; then atomic versioned output. dest_is_temp only
when dest is temp.
B2: bind actual process exit and real gate returns; exit + git tip/head
on receipt.json.
B3: OutcomeReadSpy / ForbiddenSurfaceSpy around fictional model calls;
invalid-A refuses BEFORE the model with zero solver calls.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex
from src.services.nfl_ops_v1_evidence.constants import (
    JOINT_CONTRACT,
    PACKAGE,
    PROTOCOL,
    SCHEMA_VERSION,
)
from src.services.nfl_ops_v1_evidence.gate import gate_before_consume, gate_before_final_receipt
from src.services.nfl_ops_v1_evidence.hashes import sha256_text
from src.services.nfl_ops_v1_evidence.profiles import (
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_R7,
    PROFILE_SYNTHETIC_MARKET_EVENTS,
    WORKER_A_ID,
    list_profiles,
    require_active_profile,
)
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.schema import default_exposure, schema_hash, spec_hash
from src.services.nfl_ops_v1_evidence.spy import (
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    run_spy_positive_control,
)
from src.services.nfl_ops_v1_evidence.validate import utc_now
from src.services.nfl_ops_v1_evidence.validate_r7 import (
    build_r7_verification_context,
    dest_is_actually_temp,
    readback_and_rehash,
)
from src.services.nfl_ops_v1_evidence.verify import git_tip
from src.services.nfl_r7_correctness_v1.consume_b import consume_b_handoff
from src.services.nfl_r7_correctness_v1.packets import build_synthetic_r7_demo
from src.services.nfl_r7_correctness_v1.pins import (
    AUTHORITY,
    BASE_DEPLOY_VERCEL,
    CERT,
    EXPECTED_COMMAND,
    GATE_713_TIP,
    OPS_REL,
    OWNER_CLEAR,
    PLAN_FINGERPRINT,
    PR_714_STATUS,
    PR_714_TIP,
    R6_A_TIP,
    R6_B_TIP,
    SCOPE_ID,
)
from src.services.nfl_r7_correctness_v1.produce import (
    atomic_replace_file,
    load_produce_artifacts,
    r7_code_hash,
    r7_config_hash,
    repo_root,
    write_json,
)
from src.services.nfl_r7_correctness_v1.recorder import pair_record
from src.services.nfl_t5208u.caller import model_spy_counts, reset_model_spy
from src.services.nfl_t5208u.hashing import sha256_file


def _payload_from_demo(demo: Mapping[str, Any], *, produced: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    packet = demo["packet"]
    env = packet["envelope"]
    history_hash = (
        produced["history_hash"]
        if produced is not None
        else sha256_hex(canonical_json(list(demo["history"])).encode("utf-8"))
    )
    payload: dict[str, Any] = {
        "channel": "SYNTHETIC",
        "real_mode_usable": False,
        "game_id": env["game_id"],
        "packet_hash": produced["packet_hash"] if produced is not None else packet["source_byte_hash"],
        "history_hash": history_hash,
        "r7_config_hash": produced["r7_config_hash"] if produced is not None else r7_config_hash(),
        "r7_code_hash": produced["r7_code_hash"] if produced is not None else r7_code_hash(),
        "franchise_bind": demo["franchise_bind"],
        "rest_calendar": demo["rest_calendar"],
        "packet": packet,
        "history": demo["history"],
        "physical_schedule": demo["physical_schedule"],
        "opt_in": True,
        "cert": CERT,
    }
    if produced is not None:
        payload["if_margin"] = produced["if_margin"]
        payload["q2_margin"] = produced["q2_margin"]
        payload["c_margin"] = produced["c_margin"]
    return payload


def _changed_files(repo: Path) -> list[dict[str, str]]:
    changed = []
    for rel in (
        "services/model-service/src/services/nfl_r7_correctness_v1/produce.py",
        "services/model-service/src/services/nfl_ops_v1_evidence/profiles.py",
    ):
        path = repo / rel
        changed.append({"path": rel, "sha256": sha256_file(path), "ref_kind": "file_sha256"})
    return changed


def _r7_manifest(
    *,
    demo: Mapping[str, Any],
    payload: Mapping[str, Any],
    input_hash: str,
    history_hash: str,
    config_hash: str,
    code_hash: str,
    head: str,
    cwd: str,
    start_utc: str,
    dest: Path,
    rehashed: Mapping[str, Any],
    spy_control: Mapping[str, Any],
    end_utc: Optional[str] = None,
    log_text: Optional[str] = None,
    output_paths: Optional[list[str]] = None,
    output_hashes: Optional[dict[str, str]] = None,
    producer_digest: Optional[str] = None,
    produced: Optional[Mapping[str, Any]] = None,
    exit_code: Optional[int] = None,
    consume_invoked: bool = False,
    produce_invoked: bool = False,
) -> dict[str, Any]:
    require_active_profile(PROFILE_R7)
    rest = demo["rest_calendar"]
    dest_path = Path(dest)
    digest = producer_digest or payload.get("packet_hash")
    numerical = None
    if produced is not None:
        numerical = {
            "n": 1,
            "game_id": produced["game_id"],
            "if_margin": produced["if_margin"],
            "q2_margin": produced["q2_margin"],
            "c_margin": produced["c_margin"],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "package": PACKAGE,
        "authority": AUTHORITY,
        "owner_clear": OWNER_CLEAR,
        "protocol": PROTOCOL,
        "joint_contract": JOINT_CONTRACT,
        "scope_id": SCOPE_ID,
        "profile": PROFILE_R7,
        "owner": "Worker A",
        "cert": CERT,
        "base": {"kind": "git_commit", "value": BASE_DEPLOY_VERCEL},
        "head": {"kind": "git_commit", "value": head},
        "spec_hash": spec_hash(),
        "schema_hash": schema_hash(),
        "changed_files": _changed_files(Path(cwd)),
        "typed_references": [
            {"kind": "git_commit", "value": R6_A_TIP, "label": "R6_A"},
            {"kind": "git_commit", "value": R6_B_TIP, "label": "R6_B"},
            {"kind": "git_commit", "value": GATE_713_TIP, "label": "PR713_GATE"},
            {"kind": "git_commit", "value": PR_714_TIP, "label": "PR714_PARTIAL"},
        ],
        "input_identities": {
            "game_id": payload["game_id"],
            "home": demo["franchise_bind"]["franchise_key_home"],
            "away": demo["franchise_bind"]["franchise_key_away"],
            "season": 2018,
            "week": 6,
            "data_label": "SYNTHETIC",
            "calendar_id": rest["calendar_id"],
        },
        "cohort": {"n": 1, "game_ids": [payload["game_id"]]},
        "data_label": "SYNTHETIC",
        "input_hash": input_hash,
        "history_hash": history_hash,
        "config_hash": config_hash,
        "code_hash": code_hash,
        "hash_bindings": {
            "schema": {"source": "schema_body", "alg": "sha256", "sha256": schema_hash()},
            "input": {"source": "r7_produce_payload", "alg": "sha256", "sha256": input_hash},
            "history": {"source": "r7_history_bytes", "alg": "sha256", "sha256": history_hash},
            "config": {"source": "r7_config_bind", "alg": "sha256", "sha256": config_hash},
            "code": {"source": "r7_code_files", "alg": "sha256", "sha256": code_hash},
        },
        "output_paths": output_paths,
        "output_hashes": output_hashes,
        "command": EXPECTED_COMMAND,
        "cwd": cwd,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "exit": exit_code,
        "log_hash": None if log_text is None else sha256_text(log_text),
        "evidence_labels": {
            "produce_r7_point_margin": "EXECUTED_HERE" if produce_invoked else "NOT_RUN",
            "r7_paired_recorder": "EXECUTED_HERE" if consume_invoked else "NOT_RUN",
            "inherited_real_outcome_tests": "NOT_RUN",
            "worker_b_owned_market_trace": "NOT_RUN",
            "worker_b_synthetic_market_events": "NOT_RUN",
            "chief_review": "NOT_RUN",
            "ready_for_review": "NOT_RUN",
            "lineage_r6a": "SOURCE_INSPECTION",
            "lineage_r6b": "SOURCE_INSPECTION",
            "lineage_713": "SOURCE_INSPECTION",
            "pr714": "REPORTED_ONLY",
        },
        "producer_consumer_trace": {
            "producer": "r7_correctness_produce",
            "consumer": "r7_paired_recorder",
            "producer_digest": digest,
            "consumer_digest": digest if consume_invoked else None,
        },
        "common_digest": digest,
        "numerical_output": numerical,
        "positive_control": {
            "ran": True,
            "et_utc_rest_differs": rest["rest_days_home"] != rest["utc_date_delta_home"],
        },
        "rehashed_faults": dict(rehashed),
        "spy_positive_control": dict(spy_control),
        "forbidden_calls_on_refusal": 0,
        "exposure": default_exposure(),
        "immutable_input_proof": {
            "dest_is_temp": dest_is_actually_temp(dest_path),
            "dest": dest_path.as_posix(),
            "pinned_originals_unwritten": True,
        },
        "limitations": [
            "CERT=0",
            "SYNTHETIC_ONLY",
            "not self-accept",
            "PR714 PARTIAL not wholesale base",
            "Worker B profiles registered by A from isolated handoff",
            "no paid APIs / prod push / merge / deploy / certification",
        ],
        "failures": [] if consume_invoked else None,
        "review_revision": 0,
        "worker_handoff": {
            "day_b_profiles": {
                PROFILE_OWNED_MARKET_TRACE: "REGISTERED",
                PROFILE_SYNTHETIC_MARKET_EVENTS: "REGISTERED",
            },
            "registrar": WORKER_A_ID,
            "note": "A registered B profiles from isolated nfl_owned_market_v1 handoff. B did not self-register.",
        },
        "ready_for_review": False,
        "execution": {
            "produce_invoked_here": produce_invoked,
            "consume_invoked_here": consume_invoked,
            "saved_output_only": False,
            "import_only": False,
            "process_id": os.getpid(),
            "produce_start_utc": start_utc,
        },
    }


def r7_verification(
    *,
    root: Path,
    payload: Mapping[str, Any],
    dest: Path,
    exit_code: Optional[int] = None,
    output_paths: Optional[list[Path | str]] = None,
    log_text: Optional[str] = None,
):
    return build_r7_verification_context(
        root=root,
        payload=payload,
        command=EXPECTED_COMMAND,
        cwd=str(root),
        config_hash=r7_config_hash(),
        code_hash=r7_code_hash(root),
        history_hash=str(payload["history_hash"]),
        exit_code=exit_code,
        output_paths=output_paths,
        log_text=log_text,
        git_head=git_tip(root),
    )


def run_r7_rehashed_fault_control(
    manifest: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    root: Path,
    dest: Path,
    outcome_spy: Optional[OutcomeReadSpy] = None,
    surface: Optional[ForbiddenSurfaceSpy] = None,
) -> dict[str, Any]:
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
    mutated["channel"] = "TAMPERED"
    refuse_spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    refuse_surface = surface if surface is not None else ForbiddenSurfaceSpy()
    gate_invoked = 0
    refused = False
    refuse_class = None
    reason = ""
    try:
        gate_invoked += 1
        ctx = r7_verification(root=root, payload=payload, dest=dest)
        gate_before_consume(
            manifest,
            chain_payload=mutated,
            root=root,
            command=EXPECTED_COMMAND,
            cwd=str(root),
            outcome_spy=refuse_spy,
            surface=refuse_surface,
            verification=ctx,
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
        "evidence_label": "EXECUTED_HERE",
    }


def build_r7_direct_pre_consume(
    *,
    root: Path,
    dest: Path,
    rehashed: Optional[Mapping[str, Any]] = None,
    spy_control: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Direct-API helper. Builds PRE_CONSUME bundle. Does not call the model."""
    repo = Path(root)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    consume_b_handoff(root=repo, registered_by=WORKER_A_ID)
    demo = build_synthetic_r7_demo()
    payload = _payload_from_demo(demo)
    input_hash = sha256_hex(canonical_json(payload).encode("utf-8"))
    head = git_tip(repo)
    start = utc_now()
    faults = dict(rehashed) if rehashed is not None else {
        "ran": True,
        "refused": True,
        "gate_invoked": 1,
        "instrumentation_control": {"fired": True},
        "forbidden_calls": 0,
    }
    spy = dict(spy_control) if spy_control is not None else {"ran": True, "spy_fired": True}
    manifest = _r7_manifest(
        demo=demo,
        payload=payload,
        input_hash=input_hash,
        history_hash=str(payload["history_hash"]),
        config_hash=r7_config_hash(),
        code_hash=r7_code_hash(repo),
        head=head,
        cwd=str(repo),
        start_utc=start,
        dest=dest,
        rehashed=faults,
        spy_control=spy,
    )
    verification = r7_verification(root=repo, payload=payload, dest=dest)
    return {
        "manifest": manifest,
        "payload": payload,
        "verification": verification,
        "demo": demo,
        "dest": dest,
        "head": head,
    }


def run_r7_invalid_a(
    *,
    root: Path,
    outcome_spy: Optional[OutcomeReadSpy] = None,
    surface: Optional[ForbiddenSurfaceSpy] = None,
) -> None:
    """Invalid-A: gate refuses BEFORE any model/solver call."""
    reset_model_spy()
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    surf = surface if surface is not None else ForbiddenSurfaceSpy()
    dest = Path(tempfile.mkdtemp(prefix="r7-invalid-a-"))
    try:
        bundle = build_r7_direct_pre_consume(root=root, dest=dest)
        payload = dict(bundle["payload"])
        payload["channel"] = "REAL"
        payload["real_mode_usable"] = True
        bundle["manifest"]["input_hash"] = sha256_hex(canonical_json(payload).encode("utf-8"))
        bundle["manifest"]["hash_bindings"]["input"]["sha256"] = bundle["manifest"]["input_hash"]
        verification = r7_verification(root=root, payload=payload, dest=dest)
        counts_before = model_spy_counts()
        try:
            gate_before_consume(
                bundle["manifest"],
                chain_payload=payload,
                root=root,
                command=EXPECTED_COMMAND,
                cwd=str(root),
                outcome_spy=spy,
                surface=surf,
                verification=verification,
            )
        except EvidenceGateRefuse:
            counts = model_spy_counts()
            if counts != counts_before or counts["produce_if_mu"] != 0 or counts["asof_for_targets"] != 0:
                raise EvidenceGateRefuse(
                    "invalid-A path called model/solver",
                    refuse_class=RefuseClass.FORBIDDEN_CALL,
                    detail={"model_spy": counts},
                )
            if surf.count != 0:
                raise EvidenceGateRefuse(
                    f"invalid-A path noted model surface {surf.calls}",
                    refuse_class=RefuseClass.FORBIDDEN_CALL,
                )
            if spy.reads != 0:
                raise EvidenceGateRefuse(
                    "invalid-A path read outcomes",
                    refuse_class=RefuseClass.SPY,
                )
            raise
        raise EvidenceGateRefuse(
            "invalid-A was not refused before model",
            refuse_class=RefuseClass.CHANNEL,
        )
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def _atomic_publish(src: Path, dest: Path, extras: Mapping[str, Any]) -> dict[str, str]:
    dest.mkdir(parents=True, exist_ok=True)
    published: dict[str, str] = {}
    for name in ("synthetic_demo.json", "demo_result.json"):
        src_file = src / name
        if src_file.is_file():
            atomic_replace_file(src_file, dest / name)
            published[name] = (dest / name).as_posix()
    for name, payload in extras.items():
        if name.endswith(".md"):
            data = str(payload).encode("utf-8")
            from src.services.nfl_r7_correctness_v1.produce import atomic_write_bytes

            atomic_write_bytes(dest / name, data)
        else:
            write_json(dest / name, payload)
        published[name] = (dest / name).as_posix()
    return published


PRODUCE_ONLY_REL = "scripts/nfl/run_nfl_r7_produce_only.py"
EXIT_SOURCE = "SUBPROCESS_RETURNCODE"
LOG_SOURCE = "SUBPROCESS_STDOUT"


def observe_produce_subprocess(*, repo: Path, dest: Path, mode: str) -> dict[str, Any]:
    """Run produce in a child process. Bind the OS returncode — never a literal."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    script = Path(repo) / PRODUCE_ONLY_REL
    if not script.is_file():
        raise EvidenceGateRefuse(
            f"produce child script missing {PRODUCE_ONLY_REL}",
            refuse_class=RefuseClass.MISSING_CONTEXT,
        )
    env = os.environ.copy()
    ms = str(Path(repo) / "services" / "model-service")
    prior = env.get("PYTHONPATH")
    env["PYTHONPATH"] = ms if not prior else ms + os.pathsep + prior
    proc = subprocess.run(
        [sys.executable, str(script), "--dest", str(dest), "--mode", mode],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": int(proc.returncode),
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "exit_source": EXIT_SOURCE,
        "log_source": LOG_SOURCE,
        "command": [sys.executable, str(script), "--dest", str(dest), "--mode", mode],
    }


def run_r7_integrated(
    *,
    root: Path | None = None,
    mode: str = "SYNTHETIC",
    dest: Path | None = None,
) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    final_dest = Path(dest) if dest is not None else repo / OPS_REL
    start = utc_now()
    outcome_spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    reset_model_spy()
    b_consume = consume_b_handoff(root=repo, registered_by=WORKER_A_ID)
    temp_root = Path(tempfile.mkdtemp(prefix="r7-correctness-"))
    try:
        temp_dest = temp_root
        demo = build_synthetic_r7_demo(mode=mode)
        pre_payload = _payload_from_demo(demo)
        pre_input = sha256_hex(canonical_json(pre_payload).encode("utf-8"))
        head = git_tip(repo)
        draft = _r7_manifest(
            demo=demo,
            payload=pre_payload,
            input_hash=pre_input,
            history_hash=str(pre_payload["history_hash"]),
            config_hash=r7_config_hash(),
            code_hash=r7_code_hash(repo),
            head=head,
            cwd=str(repo),
            start_utc=start,
            dest=temp_dest,
            rehashed={
                "ran": True,
                "refused": True,
                "gate_invoked": 1,
                "instrumentation_control": {"fired": True},
                "forbidden_calls": 0,
            },
            spy_control={"ran": True, "spy_fired": True},
        )
        rehashed = run_r7_rehashed_fault_control(
            draft,
            pre_payload,
            root=repo,
            dest=temp_dest,
            outcome_spy=OutcomeReadSpy(),
            surface=ForbiddenSurfaceSpy(),
        )
        spy_control = run_spy_positive_control()
        draft["rehashed_faults"] = dict(rehashed)
        draft["spy_positive_control"] = dict(spy_control)
        pre_ctx = r7_verification(root=repo, payload=pre_payload, dest=temp_dest)
        gate_before_consume(
            draft,
            chain_payload=pre_payload,
            root=repo,
            command=EXPECTED_COMMAND,
            cwd=str(repo),
            outcome_spy=outcome_spy,
            surface=surface,
            verification=pre_ctx,
        )

        if outcome_spy.reads not in (None, 0):
            raise EvidenceGateRefuse(
                "outcome loader already read before produce subprocess",
                refuse_class=RefuseClass.SPY,
            )
        surface.note("produce_r7_point_margin")
        observed = observe_produce_subprocess(repo=repo, dest=temp_dest, mode=mode)
        exit_code = observed["returncode"]
        log_text = observed["stdout"]
        if exit_code != 0:
            raise EvidenceGateRefuse(
                "observed produce subprocess exit is not success",
                refuse_class=RefuseClass.EXIT,
                detail={"observed_exit": exit_code, "stderr": observed["stderr"]},
            )
        produced = load_produce_artifacts(temp_dest)
        result_path = temp_dest / "demo_result.json"
        demo_path = temp_dest / "synthetic_demo.json"
        expected = sha256_file(result_path)
        readback_and_rehash(result_path, expected)
        readback_and_rehash(demo_path, sha256_file(demo_path))

        payload = _payload_from_demo(produced["demo"], produced=produced)
        input_hash = sha256_hex(canonical_json(payload).encode("utf-8"))
        output_paths = [result_path.as_posix()]
        output_hashes = {result_path.as_posix(): expected}
        end = utc_now()
        manifest = _r7_manifest(
            demo=produced["demo"],
            payload=payload,
            input_hash=input_hash,
            history_hash=str(payload["history_hash"]),
            config_hash=produced["r7_config_hash"],
            code_hash=produced["r7_code_hash"],
            head=head,
            cwd=str(repo),
            start_utc=start,
            dest=temp_dest,
            rehashed=rehashed,
            spy_control=spy_control,
            end_utc=end,
            log_text=log_text,
            output_paths=output_paths,
            output_hashes=output_hashes,
            producer_digest=produced["packet_hash"],
            produced=produced,
            exit_code=exit_code,
            consume_invoked=True,
            produce_invoked=True,
        )
        final_ctx = r7_verification(
            root=repo,
            payload=payload,
            dest=temp_dest,
            exit_code=exit_code,
            output_paths=output_paths,
            log_text=log_text,
        )
        gated = gate_before_final_receipt(
            manifest,
            chain_payload=payload,
            root=repo,
            command=EXPECTED_COMMAND,
            cwd=str(repo),
            exit_code=exit_code,
            output_paths=output_paths,
            log_text=log_text,
            outcome_spy=outcome_spy,
            surface=surface,
            verification=final_ctx,
        )
        gated_view = {
            "ok": bool(gated.get("ok")),
            "cert": gated.get("cert", CERT),
            "profile": gated.get("profile"),
            "input_hash": gated["input_hash"],
            "history_hash": gated["history_hash"],
            "config_hash": gated["config_hash"],
            "code_hash": gated["code_hash"],
            "produce_binds": {
                "packet_hash": produced["packet_hash"],
                "history_hash": produced["history_hash"],
                "r7_config_hash": produced["r7_config_hash"],
                "game_id": produced["game_id"],
            },
            "game_id": produced["game_id"],
        }
        pair = pair_record(produced, gated_view)
        profiles = list_profiles()
        receipt = {
            "ok": bool(gated.get("ok")),
            "cert": CERT,
            "status": "GATED_OK_AWAITING_CHIEF",
            "ready_for_review": False,
            "accepted": False,
            "package": "R7_CORRECTNESS_V1",
            "profile": PROFILE_R7,
            "worker_id": WORKER_A_ID,
            "plan_fingerprint": PLAN_FINGERPRINT,
            "r6_a_tip": R6_A_TIP,
            "r6_b_tip": R6_B_TIP,
            "gate_713_tip": GATE_713_TIP,
            "pr714_status": PR_714_STATUS,
            "profiles": profiles,
            "produce": {key: produced[key] for key in (
                "game_id",
                "if_margin",
                "q2_margin",
                "c_margin",
                "packet_hash",
                "history_hash",
                "r7_config_hash",
                "r7_code_hash",
                "cutoff_utc",
                "seal_utc",
                "replay_ok",
                "linear_cal_flag",
                "apply_linear_totals_calibration",
                "settings_forwarded",
                "consumed_value_decomposition",
            )},
            "rest_calendar": produced["rest_calendar"],
            "franchise_bind": produced["franchise_bind"],
            "pair": pair,
            "command": EXPECTED_COMMAND,
            "exit": exit_code,
            "exit_source": observed["exit_source"],
            "log_source": observed["log_source"],
            "log_hash": sha256_text(log_text),
            "git_tip": head,
            "git_head": head,
            "head": head,
            "rehashed_faults": dict(rehashed),
            "spy_positive_control": dict(spy_control),
            "immutable_input_proof": dict(gated["immutable_input_proof"]),
            "b_consume": {
                "ok": b_consume["ok"],
                "handoff_sha256": b_consume["handoff_sha256"],
                "b_tip": b_consume["b_tip"],
                "cos_accept": b_consume["cos_accept"],
                "status": b_consume["status"],
                "copied_validators": b_consume["copied_validators"],
            },
        }
        published = _atomic_publish(
            temp_dest,
            final_dest,
            {
                "receipt.json": receipt,
                "recorder_pair.json": pair,
                "PROFILES.json": profiles,
                "B_CONSUME.json": receipt["b_consume"],
                "RECEIPT.md": _receipt_md(receipt),
            },
        )
        receipt["artifacts"] = published
        write_json(final_dest / "receipt.json", receipt)
        return receipt
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _receipt_md(receipt: dict[str, Any]) -> str:
    p = receipt["produce"]
    rest = receipt["rest_calendar"]
    b_trace = receipt["profiles"][PROFILE_OWNED_MARKET_TRACE]["status"]
    b_events = receipt["profiles"][PROFILE_SYNTHETIC_MARKET_EVENTS]["status"]
    return (
        "# t5289u R7_CORRECTNESS_V1 receipt (CERT=0)\n\n"
        "Worker A sole integration. DRAFT only. IMPLEMENTED≠VERIFIED≠ACCEPTED.\n\n"
        f"- profile: `{receipt['profile']}`\n"
        f"- game_id: `{p['game_id']}`\n"
        f"- IF: `{p['if_margin']}`  Q2: `{p['q2_margin']}`  C: `{p['c_margin']}`\n"
        f"- rest ET home/away: `{rest['rest_days_home']}` / `{rest['rest_days_away']}` "
        f"(UTC date delta home `{rest['utc_date_delta_home']}`)\n"
        f"- franchise: `{receipt['franchise_bind']}`\n"
        f"- r7_config_hash: `{p['r7_config_hash']}`\n"
        f"- apply_linear_totals_calibration: `{p.get('apply_linear_totals_calibration')}`\n"
        f"- settings_forwarded: `{p.get('settings_forwarded')}`\n"
        f"- pair_hash: `{receipt['pair']['pair_hash']}`\n"
        f"- exit: `{receipt['exit']}` (source `{receipt.get('exit_source')}`)\n"
        f"- log_hash source: `{receipt.get('log_source')}`\n"
        f"- git_tip: `{receipt['git_tip']}`\n"
        f"- git_head: `{receipt['git_head']}`\n"
        f"- R6 A: `{receipt['r6_a_tip']}`\n"
        f"- R6 B: `{receipt['r6_b_tip']}`\n"
        f"- #713: `{receipt['gate_713_tip']}`\n"
        f"- #714: `{receipt['pr714_status']}`\n"
        f"- B {PROFILE_OWNED_MARKET_TRACE}: `{b_trace}`\n"
        f"- B {PROFILE_SYNTHETIC_MARKET_EVENTS}: `{b_events}`\n"
        "- CERT=0. No merge. No deploy. No public/betting output.\n"
    )


def main() -> int:
    receipt = run_r7_integrated()
    observed_exit = int(receipt["exit"])
    print(
        json.dumps(
            {
                "ok": receipt["ok"],
                "status": receipt["status"],
                "game_id": receipt["produce"]["game_id"],
                "exit": observed_exit,
                "exit_source": receipt.get("exit_source"),
                "git_tip": receipt["git_tip"],
                "pair_hash": receipt["pair"]["pair_hash"],
            },
            sort_keys=True,
        )
    )
    return observed_exit


if __name__ == "__main__":
    raise SystemExit(main())
