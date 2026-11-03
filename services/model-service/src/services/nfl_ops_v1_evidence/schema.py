"""Evidence-manifest schema body + builders. CERT=0."""

from __future__ import annotations

from typing import Any, Mapping

from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex
from src.services.nfl_ops_v1_evidence.constants import (
    AUTHORITY,
    CERT,
    DATA_LABEL,
    DEFAULT_LIMITATIONS,
    EVIDENCE_LABELS,
    JOINT_CONTRACT,
    OWNER,
    OWNER_CLEAR,
    PACKAGE,
    PROFILE,
    PROTOCOL,
    REQUIRED_TOP_LEVEL,
    SCHEMA_VERSION,
    SCOPE_ID,
    TYPED_REF_KINDS,
)
from src.services.nfl_ops_v1_evidence.worker_handoff import empty_worker_handoff_slot


def schema_body() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "required_top_level": list(REQUIRED_TOP_LEVEL),
        "evidence_labels": sorted(EVIDENCE_LABELS),
        "typed_ref_kinds": sorted(TYPED_REF_KINDS),
        "data_label": DATA_LABEL,
        "cert": CERT,
        "profile": PROFILE,
    }


def spec_body() -> dict[str, Any]:
    return {
        "package": PACKAGE,
        "authority": AUTHORITY,
        "owner_clear": OWNER_CLEAR,
        "protocol": PROTOCOL,
        "joint_contract": JOINT_CONTRACT,
        "scope_id": SCOPE_ID,
        "owner": OWNER,
        "section": "NFL_OPS_V1 §1 EVIDENCE GATEKEEPER",
        "cert": CERT,
    }


def schema_hash() -> str:
    return sha256_hex(canonical_json(schema_body()).encode("utf-8"))


def spec_hash() -> str:
    return sha256_hex(canonical_json(spec_body()).encode("utf-8"))


def history_none_binding() -> dict[str, Any]:
    return {
        "history": "NONE",
        "reason": "SYNTHETIC_NO_HISTORY_JOIN",
        "real_outcomes_joined": False,
    }


def default_exposure() -> dict[str, Any]:
    return {
        "subscriber_consumable": False,
        "betting_consumable": False,
        "production_consumable": False,
        "env_bypass_honored": False,
        "cacheable": False,
        "public_output": False,
        "cert": CERT,
    }


def default_evidence_labels() -> dict[str, str]:
    return {
        "produce_fixture_chain": "EXECUTED_HERE",
        "consume_fixture_chain": "EXECUTED_HERE",
        "inherited_real_outcome_tests": "NOT_RUN",
        "primary_b_worker_handoff": "NOT_RUN",
        "chief_review": "NOT_RUN",
        "ready_for_review": "NOT_RUN",
        "rehashed_faults": "EXECUTED_HERE",
        "spy_positive_control": "EXECUTED_HERE",
        "lineage_707": "SOURCE_INSPECTION",
        "lineage_706": "SOURCE_INSPECTION",
        "utility_700": "SOURCE_INSPECTION",
        "utility_701": "SOURCE_INSPECTION",
    }


def empty_execution() -> dict[str, Any]:
    return {
        "produce_invoked_here": False,
        "consume_invoked_here": False,
        "saved_output_only": False,
        "import_only": False,
        "process_id": None,
        "produce_start_utc": None,
    }


def skeleton_manifest() -> dict[str, Any]:
    """All required keys present. Not a passing manifest. Not an allow object."""
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
        "base": {"kind": "git_commit", "value": None},
        "head": {"kind": "git_commit", "value": None},
        "spec_hash": spec_hash(),
        "schema_hash": schema_hash(),
        "changed_files": [],
        "typed_references": [],
        "input_identities": {},
        "cohort": {},
        "data_label": DATA_LABEL,
        "input_hash": None,
        "history_hash": None,
        "config_hash": None,
        "code_hash": None,
        "hash_bindings": {},
        "output_paths": None,
        "output_hashes": None,
        "command": None,
        "cwd": None,
        "start_utc": None,
        "end_utc": None,
        "exit": None,
        "log_hash": None,
        "evidence_labels": default_evidence_labels(),
        "producer_consumer_trace": {},
        "common_digest": None,
        "numerical_output": None,
        "positive_control": {},
        "rehashed_faults": {},
        "spy_positive_control": {},
        "forbidden_calls_on_refusal": 0,
        "exposure": default_exposure(),
        "immutable_input_proof": {},
        "limitations": list(DEFAULT_LIMITATIONS),
        "failures": None,
        "review_revision": 0,
        "worker_handoff": empty_worker_handoff_slot(),
        "ready_for_review": False,
        "execution": empty_execution(),
    }


def identities_from_chain(payload: Mapping[str, Any]) -> dict[str, Any]:
    forecast = payload.get("forecast") if isinstance(payload.get("forecast"), Mapping) else {}
    l1 = payload.get("l1_candidate") if isinstance(payload.get("l1_candidate"), Mapping) else {}
    game_id = str(payload.get("game_id") or forecast.get("game_id") or "")
    parts = game_id.split("_")
    season = int(parts[0]) if parts and parts[0].isdigit() else None
    week = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    away = parts[2] if len(parts) > 2 else None
    home = parts[3] if len(parts) > 3 else None
    return {
        "game_id": game_id,
        "team": l1.get("team"),
        "season": season,
        "week": week,
        "away": away,
        "home": home,
        "period": forecast.get("period"),
        "book": (payload.get("quote") or {}).get("book")
        if isinstance(payload.get("quote"), Mapping)
        else None,
        "event_id": (payload.get("quote") or {}).get("event_id")
        if isinstance(payload.get("quote"), Mapping)
        else None,
        "freshness": "OBSERVED"
        if l1.get("missing_enum") == "OBSERVED"
        else l1.get("missing_enum"),
        "availability": l1.get("factor"),
        "observation": l1.get("missing_enum"),
        "data_label": DATA_LABEL,
    }
