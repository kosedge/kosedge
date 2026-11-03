"""Build / validate / serialize the worker release/claim record.

Stable shape for Primary A's evidence-manifest ``worker_handoff`` field.
No invented defaults. CERT=0. synthetic=True required.
"""

from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from .hashutil import canonical_json, sha256_canonical, sha256_text
from .types import (
    CAPABILITY_ABSENT,
    CERT,
    EVIDENCE_NOT_RUN,
    EVIDENCE_LABELS,
    OWNER_CLEAR,
    PROTOCOL_HASH,
    PROTOCOL_NAME,
    RELEASE_KINDS,
    RELEASE_NOT_RELEASED,
    REQUIRED_TOP_LEVEL,
    SCHEMA_ID,
    SCHEMA_VERSION,
    SCOPE_ID,
    STATE_WRITING,
    STATES,
    WORKER_HANDOFF_FIELD,
    WORKER_HANDOFF_KEYS,
    WorkerReleaseRefuse,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or isinstance(value, (str, bytes)):
        raise WorkerReleaseRefuse(f"{name} must be an object", code="TYPE_ERROR")
    return dict(value)


def _require_str(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if isinstance(value, bool) or not isinstance(value, str):
        raise WorkerReleaseRefuse(f"{name} must be a string", code="TYPE_ERROR")
    if not allow_empty and not value.strip():
        raise WorkerReleaseRefuse(f"{name} missing", code="MISSING_FIELD")
    return value


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise WorkerReleaseRefuse(f"{name} must be a bool", code="TYPE_ERROR")
    return value


def _require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkerReleaseRefuse(f"{name} must be an int", code="TYPE_ERROR")
    return value


def _refuse_nonfinite(value: Any, name: str) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise WorkerReleaseRefuse(f"{name} is non-finite", code="NONFINITE")


def _walk_refuse_nonfinite(value: Any, prefix: str) -> None:
    _refuse_nonfinite(value, prefix)
    if isinstance(value, Mapping):
        for key, inner in value.items():
            _walk_refuse_nonfinite(inner, f"{prefix}.{key}")
    elif isinstance(value, list):
        for idx, inner in enumerate(value):
            _walk_refuse_nonfinite(inner, f"{prefix}[{idx}]")


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise WorkerReleaseRefuse(f"{name} must be a list", code="TYPE_ERROR")
    return value


def _git_sha(value: Any, name: str) -> str:
    text = _require_str(value, name)
    if len(text) < 40 or any(ch not in "0123456789abcdef" for ch in text.lower()):
        raise WorkerReleaseRefuse(f"{name} must be a full git sha", code="TYPE_ERROR")
    return text.lower()


def empty_release_evidence() -> dict[str, Any]:
    return {
        "kind": RELEASE_NOT_RELEASED,
        "platform_capability": CAPABILITY_ABSENT,
        "capability_id": None,
        "mocked": False,
        "limitation": None,
        "evidence_label": EVIDENCE_NOT_RUN,
        "not_a_pass": True,
        "not_cursor_workspace_reclaim": True,
        "confirmed_at_utc": None,
        "detail": None,
    }


def default_limits() -> dict[str, Any]:
    return {
        "synthetic_only": True,
        "cert": CERT,
        "no_real_data": True,
        "no_self_kill": True,
        "no_deletion": True,
        "no_forced_takeover": True,
        "self_accept": False,
    }


def default_successor() -> dict[str, Any]:
    return {"id": None, "role": None, "named": False}


def content_hash_of(record: Mapping[str, Any]) -> str:
    return sha256_canonical(record)


def bind_id_for(record: Mapping[str, Any], successor_id: str) -> str:
    """Claim bind: content hash + successor + head. Stale if any drift."""
    body = {
        "content_hash": record.get("content_hash"),
        "head": record.get("head"),
        "successor_id": successor_id,
        "workspace_alias": record.get("workspace_alias"),
        "schema": SCHEMA_ID,
    }
    return sha256_text(canonical_json(body))


def stamp_content_hash(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out.pop("content_hash", None)
    out["content_hash"] = content_hash_of(out)
    return out


def with_fields(record: Mapping[str, Any], **fields: Any) -> dict[str, Any]:
    """Replace named fields and restamp the content hash. No state skip."""
    current = validate_record(record)
    nxt = dict(current)
    for key, value in fields.items():
        if key not in REQUIRED_TOP_LEVEL:
            raise WorkerReleaseRefuse(f"unknown field {key}", code="EXTRA_FIELD")
        if key in {"schema", "schema_version", "state", "content_hash"}:
            raise WorkerReleaseRefuse(
                f"cannot patch {key} via with_fields", code="FORBIDDEN"
            )
        nxt[key] = value
    return validate_record(stamp_content_hash(nxt))


def validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if record is None:
        raise WorkerReleaseRefuse("record is null", code="NULL")
    raw = _require_mapping(record, "record")
    extra = sorted(set(raw) - set(REQUIRED_TOP_LEVEL))
    if extra:
        raise WorkerReleaseRefuse(
            "unknown top-level fields: " + ", ".join(extra), code="EXTRA_FIELD"
        )
    missing = [k for k in REQUIRED_TOP_LEVEL if k not in raw]
    if missing:
        raise WorkerReleaseRefuse(
            "missing fields: " + ", ".join(missing), code="MISSING_FIELD"
        )

    if raw["schema"] != SCHEMA_ID:
        raise WorkerReleaseRefuse("schema mismatch", code="SCHEMA")
    if _require_int(raw["schema_version"], "schema_version") != SCHEMA_VERSION:
        raise WorkerReleaseRefuse("schema_version mismatch", code="SCHEMA")
    if _require_int(raw["cert"], "cert") != CERT:
        raise WorkerReleaseRefuse("cert must be 0", code="CERT")
    if not _require_bool(raw["synthetic"], "synthetic"):
        raise WorkerReleaseRefuse("synthetic must be true", code="SYNTHETIC")
    if _require_bool(raw["self_accept"], "self_accept"):
        raise WorkerReleaseRefuse("self_accept must be false", code="SELF_ACCEPT")

    _require_str(raw["scope_id"], "scope_id")
    _require_str(raw["protocol"], "protocol")
    _require_str(raw["protocol_hash"], "protocol_hash")
    _require_str(raw["owner_clear"], "owner_clear")
    _require_str(raw["branch"], "branch")
    _git_sha(raw["head"], "head")
    _require_str(raw["workspace_alias"], "workspace_alias")

    task = _require_mapping(raw["task"], "task")
    _require_str(task.get("id"), "task.id")
    _require_str(task.get("role"), "task.role")
    _require_str(task.get("title"), "task.title")

    worker = _require_mapping(raw["worker"], "worker")
    _require_str(worker.get("id"), "worker.id")
    _require_str(worker.get("kind"), "worker.kind")

    dirty = _require_mapping(raw["dirty"], "dirty")
    _require_bool(dirty.get("clean"), "dirty.clean")
    _require_list(dirty.get("changed_paths"), "dirty.changed_paths")
    _require_bool(dirty.get("preserved"), "dirty.preserved")
    _require_list(raw["untracked"], "untracked")
    _require_list(raw["saved_artifacts"], "saved_artifacts")
    _require_list(raw["log_hashes"], "log_hashes")
    _require_mapping(raw["tests"], "tests")
    limits = _require_mapping(raw["limits"], "limits")
    if not _require_bool(limits.get("synthetic_only"), "limits.synthetic_only"):
        raise WorkerReleaseRefuse("limits.synthetic_only must be true", code="LIMITS")
    if not _require_bool(limits.get("no_self_kill"), "limits.no_self_kill"):
        raise WorkerReleaseRefuse("self-kill is forbidden", code="FORBIDDEN")
    if not _require_bool(limits.get("no_deletion"), "limits.no_deletion"):
        raise WorkerReleaseRefuse("deletion is forbidden", code="FORBIDDEN")
    if not _require_bool(limits.get("no_forced_takeover"), "limits.no_forced_takeover"):
        raise WorkerReleaseRefuse("forced takeover is forbidden", code="FORBIDDEN")

    writer = raw["active_writer"]
    if writer is not None:
        wmap = _require_mapping(writer, "active_writer")
        _require_str(wmap.get("id"), "active_writer.id")

    _require_list(raw["running_jobs"], "running_jobs")
    _require_list(raw["pending_prompts"], "pending_prompts")
    successor = _require_mapping(raw["successor"], "successor")
    _require_bool(successor.get("named"), "successor.named")
    if successor.get("id") is not None:
        _require_str(successor.get("id"), "successor.id")

    evidence = _require_mapping(raw["release_evidence"], "release_evidence")
    kind = _require_str(evidence.get("kind"), "release_evidence.kind")
    if kind not in RELEASE_KINDS:
        raise WorkerReleaseRefuse("unknown release_evidence.kind", code="TYPE_ERROR")
    label = _require_str(evidence.get("evidence_label"), "release_evidence.evidence_label")
    if label not in EVIDENCE_LABELS:
        raise WorkerReleaseRefuse("unknown evidence_label", code="TYPE_ERROR")
    _require_bool(evidence.get("mocked"), "release_evidence.mocked")
    _require_bool(evidence.get("not_a_pass"), "release_evidence.not_a_pass")
    if kind == RELEASE_NOT_RELEASED or kind == "PLATFORM_LIMITATION":
        if not evidence.get("not_a_pass"):
            raise WorkerReleaseRefuse(
                "PLATFORM_LIMITATION / NOT_RELEASED cannot be a PASS",
                code="NOT_A_PASS",
            )
    if evidence.get("mocked") and kind == "PLATFORM_RELEASE_CONFIRMED":
        raise WorkerReleaseRefuse(
            "mocked release is not actual platform reclaim",
            code="MOCKED_RELEASE",
        )

    state = _require_str(raw["state"], "state")
    if state not in STATES:
        raise WorkerReleaseRefuse("unknown state", code="STATE")
    _require_list(raw["state_history"], "state_history")

    _walk_refuse_nonfinite(raw, "record")

    expected = content_hash_of(raw)
    got = _require_str(raw["content_hash"], "content_hash")
    if got != expected:
        raise WorkerReleaseRefuse("content_hash mismatch", code="HASH_MISMATCH")
    return dict(raw)


def build_record(
    *,
    task: Mapping[str, Any],
    worker: Mapping[str, Any],
    branch: str,
    head: str,
    workspace_alias: str,
    dirty: Mapping[str, Any] | None = None,
    untracked: list[str] | None = None,
    saved_artifacts: list[Mapping[str, Any]] | None = None,
    log_hashes: list[Mapping[str, Any]] | None = None,
    tests: Mapping[str, Any] | None = None,
    limits: Mapping[str, Any] | None = None,
    active_writer: Mapping[str, Any] | None = None,
    running_jobs: list[Mapping[str, Any]] | None = None,
    pending_prompts: list[Mapping[str, Any]] | None = None,
    successor: Mapping[str, Any] | None = None,
    release_evidence: Mapping[str, Any] | None = None,
    scope_id: str = SCOPE_ID,
    protocol: str = PROTOCOL_NAME,
    protocol_hash: str = PROTOCOL_HASH,
    owner_clear: str = OWNER_CLEAR,
    at_utc: str | None = None,
) -> dict[str, Any]:
    now = at_utc or utc_now()
    dirty_obj = dict(dirty) if dirty is not None else {
        "clean": True,
        "changed_paths": [],
        "preserved": True,
    }
    record = {
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "cert": CERT,
        "synthetic": True,
        "self_accept": False,
        "scope_id": scope_id,
        "protocol": protocol,
        "protocol_hash": protocol_hash,
        "owner_clear": owner_clear,
        "task": dict(task),
        "worker": dict(worker),
        "branch": branch,
        "head": head,
        "workspace_alias": workspace_alias,
        "dirty": dirty_obj,
        "untracked": list(untracked or []),
        "saved_artifacts": [dict(x) for x in (saved_artifacts or [])],
        "log_hashes": [dict(x) for x in (log_hashes or [])],
        "tests": dict(tests or {"commands": [], "passed": None}),
        "limits": dict(limits or default_limits()),
        "active_writer": dict(active_writer) if active_writer is not None else None,
        "running_jobs": [dict(x) for x in (running_jobs or [])],
        "pending_prompts": [dict(x) for x in (pending_prompts or [])],
        "successor": dict(successor or default_successor()),
        "release_evidence": dict(release_evidence or empty_release_evidence()),
        "state": STATE_WRITING,
        "state_history": [{"from": None, "to": STATE_WRITING, "at_utc": now, "code": "OPEN"}],
    }
    stamped = stamp_content_hash(record)
    return validate_record(stamped)


def serialize_record(record: Mapping[str, Any]) -> str:
    validated = validate_record(record)
    return canonical_json(validated) + "\n"


def as_worker_handoff(record: Mapping[str, Any]) -> dict[str, Any]:
    """Stable plug-in object for Primary A's evidence-manifest field."""
    validated = validate_record(record)
    evidence = validated["release_evidence"]
    handoff = {
        "field": WORKER_HANDOFF_FIELD,
        "schema": validated["schema"],
        "schema_version": validated["schema_version"],
        "content_hash": validated["content_hash"],
        "state": validated["state"],
        "task_id": validated["task"]["id"],
        "worker_id": validated["worker"]["id"],
        "branch": validated["branch"],
        "head": validated["head"],
        "workspace_alias": validated["workspace_alias"],
        "release_kind": evidence["kind"],
        "evidence_label": evidence["evidence_label"],
        "platform_capability": evidence["platform_capability"],
        "mocked_release": evidence["mocked"],
        "not_a_pass": evidence["not_a_pass"],
        "record": deepcopy(validated),
    }
    extra = sorted(set(handoff) - set(WORKER_HANDOFF_KEYS))
    if extra:
        raise WorkerReleaseRefuse(
            "worker_handoff shape drifted: " + ", ".join(extra), code="SHAPE"
        )
    missing = [k for k in WORKER_HANDOFF_KEYS if k not in handoff]
    if missing:
        raise WorkerReleaseRefuse(
            "worker_handoff missing: " + ", ".join(missing), code="SHAPE"
        )
    return handoff
