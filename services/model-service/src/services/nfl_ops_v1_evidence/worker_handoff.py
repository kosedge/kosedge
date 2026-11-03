"""Bind Primary B's actual worker_handoff. Do not invent a reclaim PASS.

B tip 82683cd9 / Cos ACCEPT bc6a567d. Slot-reserved is no longer a substitute
once B is DONE. PLATFORM_LIMITATION + not_a_pass are preserved. CERT=0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_ops_v1_worker_release.record import as_worker_handoff, validate_record
from src.services.nfl_ops_v1_worker_release.types import (
    SCHEMA_ID as B_SCHEMA_ID,
    WORKER_HANDOFF_FIELD,
    WORKER_HANDOFF_KEYS,
    WorkerReleaseRefuse,
)
from src.services.nfl_ops_v1_evidence.finite import require_bool, require_str
from src.services.nfl_ops_v1_evidence.hashes import require_sha256_hex
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass

# Kept so older negative tests can still build an invented substitute.
WORKER_HANDOFF_SCHEMA = "nfl-ops-v1-worker-handoff-slot-v1"
WORKER_HANDOFF_STATES = (
    "WRITING",
    "HANDOFF_RECORDED",
    "QUIESCENT",
    "RELEASE_CONFIRMED",
    "CLAIMED_BY_SUCCESSOR",
)
WORKER_HANDOFF_RECORD_KEYS = (
    "task",
    "worker",
    "branch",
    "head",
    "workspace_alias",
    "dirty_untracked",
    "saved_artifacts",
    "log_hashes",
    "tests_limits",
    "running_processes_jobs",
    "pending_prompts",
    "successor",
    "ownership_release",
    "state",
)

B_TIP = "82683cd93ec2c231733f34b5c0372cf1d42fa68a"
B_PR = 712
B_COS_ACCEPT = "bc6a567d"
B_HANDOFF_REL = "data/ops/nfl-ops-v1-worker-release-claim/THIS_WORKER_HANDOFF.json"
B_CONTENT_HASH = "b8aa6100f29ddad29c73c2a1624beb657407303bd28b7384c9d94dc55def2981"
B_WORKER_ID = "bc-3a3acab2-0de1-51eb-80e0-8ac958dfe2c7"
B_TASK_ID = "chief-nflgreen-overnight-ops-20261102-0330-primary-b"
B_BRANCH = "cursor/nfl-ops-v1-worker-release-e2c7"
B_RECORD_HEAD = "e6cfb87341adc8c4170bc8b53c7f1a030b489a4e"
B_STATE = "QUIESCENT"
B_RELEASE_KIND = "PLATFORM_LIMITATION"

_PASS_STATUSES = frozenset(
    {"PASS", "RELEASE_CONFIRMED", "CLAIMED", "CLAIMED_BY_SUCCESSOR", "RECLAIMED"}
)


def empty_worker_handoff_slot() -> dict[str, Any]:
    """Historical A-only slot. Not a valid bind after B Cos-ACCEPT."""
    return {
        "schema": WORKER_HANDOFF_SCHEMA,
        "status": "SLOT_RESERVED",
        "bound": False,
        "record": None,
        "accepted_states": list(WORKER_HANDOFF_STATES),
        "record_required_keys": list(WORKER_HANDOFF_RECORD_KEYS),
        "mocked_release_is_pass": False,
        "note": (
            "Invented substitute. Primary B is DONE — bind THIS_WORKER_HANDOFF.json "
            "via as_worker_handoff(). SLOT_RESERVED is not PASS."
        ),
    }


def _refuse(reason: str) -> None:
    raise EvidenceGateRefuse(reason, refuse_class=RefuseClass.WORKER_HANDOFF)


def _wrap_b(exc: WorkerReleaseRefuse) -> EvidenceGateRefuse:
    return EvidenceGateRefuse(
        f"B worker_handoff refuse: {exc}",
        refuse_class=RefuseClass.WORKER_HANDOFF,
        detail={"b_code": getattr(exc, "code", None)},
    )


def load_actual_b_handoff(root: Path) -> dict[str, Any]:
    """Load B's sealed THIS_WORKER_HANDOFF and re-emit via as_worker_handoff()."""
    path = Path(root) / B_HANDOFF_REL
    if not path.is_file():
        _refuse(f"B handoff pin missing: {B_HANDOFF_REL}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or "record" not in raw:
        _refuse("B THIS_WORKER_HANDOFF.json is not a worker_handoff object")
    try:
        handoff = as_worker_handoff(raw["record"])
    except WorkerReleaseRefuse as exc:
        raise _wrap_b(exc) from exc
    if handoff.get("content_hash") != B_CONTENT_HASH:
        _refuse(
            f"as_worker_handoff content_hash {handoff.get('content_hash')} != pinned {B_CONTENT_HASH}"
        )
    if raw.get("content_hash") != B_CONTENT_HASH:
        _refuse("THIS_WORKER_HANDOFF.json content_hash drifted from Cos-accepted pin")
    return validate_worker_handoff(handoff)


def validate_worker_handoff(slot: Any) -> dict[str, Any]:
    if slot is None:
        raise EvidenceGateRefuse(
            "worker_handoff missing — incomplete",
            refuse_class=RefuseClass.INCOMPLETE,
        )
    if not isinstance(slot, Mapping):
        raise EvidenceGateRefuse(
            "worker_handoff must be an object",
            refuse_class=RefuseClass.TYPE,
        )
    raw = dict(slot)

    if raw.get("mocked_release_is_pass") is True or raw.get("mocked_release") is True:
        _refuse("mocked release is not actual platform reclaim (not PASS)")
    if raw.get("schema") == WORKER_HANDOFF_SCHEMA or raw.get("status") == "SLOT_RESERVED":
        _refuse(
            "invented-handoff substitute: SLOT_RESERVED / A-only slot is not B's actual record"
        )
    if raw.get("schema") != B_SCHEMA_ID:
        _refuse(
            f"worker_handoff.schema {raw.get('schema')!r} != B {B_SCHEMA_ID} "
            "(invented substitute)"
        )
    if raw.get("field") != WORKER_HANDOFF_FIELD:
        _refuse("worker_handoff.field must be worker_handoff")

    missing = [key for key in WORKER_HANDOFF_KEYS if key not in raw]
    if missing:
        raise EvidenceGateRefuse(
            f"B worker_handoff missing {missing}",
            refuse_class=RefuseClass.INCOMPLETE,
        )

    extra = sorted(set(raw) - set(WORKER_HANDOFF_KEYS))
    if extra:
        raise EvidenceGateRefuse(
            f"B worker_handoff extra keys {extra}",
            refuse_class=RefuseClass.EXTRA,
        )

    record = raw.get("record")
    if not isinstance(record, Mapping):
        _refuse("worker_handoff.record must be B's actual release record")
    try:
        rebuilt = as_worker_handoff(validate_record(record))
    except WorkerReleaseRefuse as exc:
        raise _wrap_b(exc) from exc

    declared = require_sha256_hex(raw.get("content_hash"), "worker_handoff.content_hash")
    if declared != B_CONTENT_HASH or rebuilt["content_hash"] != B_CONTENT_HASH:
        _refuse("invented-handoff substitute: content_hash is not B tip 82683cd9 pin")
    if rebuilt["content_hash"] != declared:
        _refuse("worker_handoff.content_hash != as_worker_handoff(record)")

    if require_str(raw.get("release_kind"), "release_kind") != B_RELEASE_KIND:
        _refuse(
            f"release_kind {raw.get('release_kind')!r} must stay PLATFORM_LIMITATION "
            "(Cursor/GH/Railway reclaim absent)"
        )
    if require_bool(raw.get("not_a_pass"), "not_a_pass") is not True:
        _refuse("B not_a_pass must stay true — do not rewrite into PASS")
    if require_bool(raw.get("mocked_release"), "mocked_release") is not False:
        _refuse("mocked_release must be false")
    if require_str(raw.get("platform_capability"), "platform_capability") != "ABSENT":
        _refuse("platform_capability must stay ABSENT (no invented PRESENT)")
    state = require_str(raw.get("state"), "worker_handoff.state")
    if state in _PASS_STATUSES:
        _refuse(
            f"state={state} invents platform reclaim — B sealed QUIESCENT + PLATFORM_LIMITATION"
        )
    if state != B_STATE:
        _refuse(f"state {state!r} != sealed B state {B_STATE}")
    if raw.get("worker_id") != B_WORKER_ID or rebuilt.get("worker_id") != B_WORKER_ID:
        _refuse("worker_id is not B's actual worker")
    if raw.get("task_id") != B_TASK_ID:
        _refuse("task_id is not B's actual task")
    if raw.get("branch") != B_BRANCH:
        _refuse("branch is not B's actual branch")
    if raw.get("head") != B_RECORD_HEAD:
        _refuse("head is not B's sealed record head (do not rewrite to a later tip)")
    return dict(rebuilt)
