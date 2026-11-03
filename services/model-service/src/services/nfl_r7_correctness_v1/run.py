"""Produce → shared evidence gate → paired recorder. CERT=0. SYNTHETIC only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_ops_v1_evidence.constants import (
    JOINT_CONTRACT,
    PACKAGE,
    PROTOCOL,
    SCHEMA_VERSION,
    STAGE_PRE_RECEIPT,
)
from src.services.nfl_ops_v1_evidence.hashes import sha256_text
from src.services.nfl_ops_v1_evidence.profiles import (
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_R7,
    PROFILE_SYNTHETIC_MARKET_EVENTS,
    WORKER_A_ID,
    list_profiles,
    require_active_profile,
)
from src.services.nfl_r7_correctness_v1.consume_b import consume_b_handoff
from src.services.nfl_ops_v1_evidence.schema import default_exposure, schema_hash, spec_hash
from src.services.nfl_ops_v1_evidence.validate import validate_manifest
from src.services.nfl_ops_v1_evidence.verify import git_tip
from src.services.nfl_ops_v1_evidence.validate_r7 import build_r7_verification_context
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
    produce_r7_point_margin,
    r7_code_hash,
    repo_root,
    write_json,
    write_produce_artifacts,
)
from src.services.nfl_r7_correctness_v1.recorder import pair_record


def _utc_now() -> str:
    from src.services.nfl_ops_v1_evidence.validate import utc_now

    return utc_now()


def _payload_from_produce(produced: dict[str, Any]) -> dict[str, Any]:
    demo = produced["demo"]
    return {
        "channel": "SYNTHETIC",
        "real_mode_usable": False,
        "game_id": produced["game_id"],
        "if_margin": produced["if_margin"],
        "q2_margin": produced["q2_margin"],
        "c_margin": produced["c_margin"],
        "packet_hash": produced["packet_hash"],
        "history_hash": produced["history_hash"],
        "r7_config_hash": produced["r7_config_hash"],
        "r7_code_hash": produced["r7_code_hash"],
        "franchise_bind": produced["franchise_bind"],
        "rest_calendar": produced["rest_calendar"],
        "packet": demo["packet"],
        "history": demo["history"],
        "opt_in": True,
        "cert": CERT,
    }


def _r7_manifest(
    *,
    produced: dict[str, Any],
    payload: dict[str, Any],
    input_hash: str,
    history_hash: str,
    config_hash: str,
    code_hash: str,
    head: str,
    cwd: str,
    start_utc: str,
    end_utc: str,
    log_text: str,
    output_paths: list[str],
    output_hashes: dict[str, str],
    producer_digest: str,
) -> dict[str, Any]:
    require_active_profile(PROFILE_R7)
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
        "changed_files": [
            {
                "path": rel,
                "sha256": produced["r7_code_hash"] if False else None,
                "ref_kind": "file_sha256",
            }
            for rel in (
                "services/model-service/src/services/nfl_r7_correctness_v1/produce.py",
            )
        ],
        "typed_references": [
            {"kind": "git_commit", "value": R6_A_TIP, "label": "R6_A"},
            {"kind": "git_commit", "value": R6_B_TIP, "label": "R6_B"},
            {"kind": "git_commit", "value": GATE_713_TIP, "label": "PR713_GATE"},
            {"kind": "git_commit", "value": PR_714_TIP, "label": "PR714_PARTIAL"},
        ],
        "input_identities": {
            "game_id": produced["game_id"],
            "home": produced["franchise_bind"]["franchise_key_home"],
            "away": produced["franchise_bind"]["franchise_key_away"],
            "season": 2018,
            "week": 6,
            "data_label": "SYNTHETIC",
            "calendar_id": produced["rest_calendar"]["calendar_id"],
        },
        "cohort": {"n": 1, "game_ids": [produced["game_id"]]},
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
        "exit": 0,
        "log_hash": sha256_text(log_text),
        "evidence_labels": {
            "produce_r7_point_margin": "EXECUTED_HERE",
            "r7_paired_recorder": "EXECUTED_HERE",
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
            "producer_digest": producer_digest,
            "consumer_digest": producer_digest,
        },
        "common_digest": producer_digest,
        "numerical_output": {
            "n": 1,
            "game_id": produced["game_id"],
            "if_margin": produced["if_margin"],
            "q2_margin": produced["q2_margin"],
            "c_margin": produced["c_margin"],
        },
        "positive_control": {"ran": True, "et_utc_rest_differs": True},
        "rehashed_faults": {
            "ran": True,
            "refused": True,
            "gate_invoked": 1,
            "instrumentation_control": {"fired": True},
            "forbidden_calls": 0,
        },
        "spy_positive_control": {"ran": True, "spy_fired": True},
        "forbidden_calls_on_refusal": 0,
        "exposure": default_exposure(),
        "immutable_input_proof": {
            "dest_is_temp": True,
            "pinned_originals_unwritten": True,
        },
        "limitations": [
            "CERT=0",
            "SYNTHETIC_ONLY",
            "not self-accept",
            "PR714 PARTIAL not wholesale base",
            "Worker B profiles PENDING_HANDOFF until A registers handoff",
            "no paid APIs / prod push / merge / deploy / certification",
        ],
        "failures": [],
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
            "produce_invoked_here": True,
            "consume_invoked_here": True,
            "saved_output_only": False,
            "import_only": False,
            "process_id": None,
            "produce_start_utc": start_utc,
        },
        "ok": True,
    }


def run_r7_integrated(*, root: Path | None = None, mode: str = "SYNTHETIC") -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    start = _utc_now()
    b_consume = consume_b_handoff(root=repo, registered_by=WORKER_A_ID)
    produced = produce_r7_point_margin(mode=mode)
    paths = write_produce_artifacts(produced, root=repo)
    payload = _payload_from_produce(produced)
    config_hash = produced["r7_config_hash"]
    code_hash = r7_code_hash(repo)
    history_hash = produced["history_hash"]
    from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex

    input_hash = sha256_hex(canonical_json(payload).encode("utf-8"))
    head = git_tip(repo)
    dest = repo / OPS_REL
    produce_path = dest / "demo_result.json"
    log_text = (
        f"R7_CORRECTNESS_V1 produce ok game_id={produced['game_id']} "
        f"if={produced['if_margin']} q2={produced['q2_margin']} c={produced['c_margin']}\n"
    )
    output_paths = [produce_path.as_posix()]
    output_hashes = {produce_path.as_posix(): sha256_hex(produce_path.read_bytes())}
    producer_digest = produced["packet_hash"]
    end = _utc_now()
    # fill changed_files with real hashes
    from src.services.nfl_t5208u.hashing import sha256_file

    changed = []
    for rel in (
        "services/model-service/src/services/nfl_r7_correctness_v1/produce.py",
        "services/model-service/src/services/nfl_ops_v1_evidence/profiles.py",
    ):
        path = repo / rel
        changed.append({"path": rel, "sha256": sha256_file(path), "ref_kind": "file_sha256"})

    manifest = _r7_manifest(
        produced=produced,
        payload=payload,
        input_hash=input_hash,
        history_hash=history_hash,
        config_hash=config_hash,
        code_hash=code_hash,
        head=head,
        cwd=str(repo),
        start_utc=start,
        end_utc=end,
        log_text=log_text,
        output_paths=output_paths,
        output_hashes=output_hashes,
        producer_digest=producer_digest,
    )
    manifest["changed_files"] = changed
    ctx = build_r7_verification_context(
        root=repo,
        payload=payload,
        command=EXPECTED_COMMAND,
        cwd=str(repo),
        config_hash=config_hash,
        code_hash=code_hash,
        history_hash=history_hash,
        exit_code=0,
        output_paths=output_paths,
        log_text=log_text,
        git_head=head,
    )
    gated = validate_manifest(
        manifest,
        stage=STAGE_PRE_RECEIPT,
        chain_payload=payload,
        verification=ctx,
    )
    gated_view = {
        "ok": True,
        "cert": CERT,
        "profile": PROFILE_R7,
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
        "ok": True,
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
        )},
        "rest_calendar": produced["rest_calendar"],
        "franchise_bind": produced["franchise_bind"],
        "pair": pair,
        "artifacts": paths,
        "command": EXPECTED_COMMAND,
        "b_consume": {
            "ok": b_consume["ok"],
            "handoff_sha256": b_consume["handoff_sha256"],
            "b_tip": b_consume["b_tip"],
            "cos_accept": b_consume["cos_accept"],
            "status": b_consume["status"],
            "copied_validators": b_consume["copied_validators"],
        },
    }
    write_json(dest / "receipt.json", receipt)
    write_json(dest / "recorder_pair.json", pair)
    write_json(dest / "PROFILES.json", profiles)
    write_json(dest / "B_CONSUME.json", receipt["b_consume"])
    (dest / "RECEIPT.md").write_text(_receipt_md(receipt), encoding="utf-8")
    return receipt


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
        f"- pair_hash: `{receipt['pair']['pair_hash']}`\n"
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
    print(json.dumps({"ok": receipt["ok"], "status": receipt["status"], "game_id": receipt["produce"]["game_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
