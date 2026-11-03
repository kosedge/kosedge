"""Primary B worker release/claim slot.

A does not wait on B and does not invent a platform reclaim PASS.
The field is required. A bound record is validated if present.
SLOT_RESERVED is not RELEASE_CONFIRMED.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.services.nfl_ops_v1_evidence.finite import require_bool, require_str
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass

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
_PASS_STATUSES = frozenset(
    {"PASS", "RELEASE_CONFIRMED", "CLAIMED", "CLAIMED_BY_SUCCESSOR", "RECLAIMED"}
)


def empty_worker_handoff_slot() -> dict[str, Any]:
    return {
        "schema": WORKER_HANDOFF_SCHEMA,
        "status": "SLOT_RESERVED",
        "bound": False,
        "record": None,
        "accepted_states": list(WORKER_HANDOFF_STATES),
        "record_required_keys": list(WORKER_HANDOFF_RECORD_KEYS),
        "mocked_release_is_pass": False,
        "note": (
            "Primary B binds the release/claim record here. "
            "SLOT_RESERVED is not PASS. Mocked platform reclaim is not PASS. "
            "Absence of a bound record does not invent RELEASE_CONFIRMED."
        ),
    }


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
    if raw.get("schema") != WORKER_HANDOFF_SCHEMA:
        raise EvidenceGateRefuse(
            f"worker_handoff.schema {raw.get('schema')!r} != {WORKER_HANDOFF_SCHEMA}",
            refuse_class=RefuseClass.WORKER_HANDOFF,
        )
    status = require_str(raw.get("status"), "worker_handoff.status")
    bound = require_bool(raw.get("bound"), "worker_handoff.bound")
    if raw.get("mocked_release_is_pass") is True:
        raise EvidenceGateRefuse(
            "mocked release is not actual platform reclaim (not PASS)",
            refuse_class=RefuseClass.WORKER_HANDOFF,
        )
    record = raw.get("record")
    if record is None:
        if bound is True:
            raise EvidenceGateRefuse(
                "worker_handoff.bound=true with null record",
                refuse_class=RefuseClass.WORKER_HANDOFF,
            )
        if status in _PASS_STATUSES:
            raise EvidenceGateRefuse(
                f"worker_handoff.status={status} without a bound record is invented PASS",
                refuse_class=RefuseClass.WORKER_HANDOFF,
            )
        if status != "SLOT_RESERVED":
            raise EvidenceGateRefuse(
                f"unbound worker_handoff.status must be SLOT_RESERVED (got {status})",
                refuse_class=RefuseClass.WORKER_HANDOFF,
            )
        return dict(raw)

    if not isinstance(record, Mapping):
        raise EvidenceGateRefuse(
            "worker_handoff.record must be an object when present",
            refuse_class=RefuseClass.TYPE,
        )
    missing = [key for key in WORKER_HANDOFF_RECORD_KEYS if key not in record]
    if missing:
        raise EvidenceGateRefuse(
            f"worker_handoff.record missing {missing}",
            refuse_class=RefuseClass.INCOMPLETE,
        )
    state = require_str(record.get("state"), "worker_handoff.record.state")
    if state not in WORKER_HANDOFF_STATES:
        raise EvidenceGateRefuse(
            f"worker_handoff.record.state {state!r} not in {WORKER_HANDOFF_STATES}",
            refuse_class=RefuseClass.WORKER_HANDOFF,
        )
    if bound is not True:
        raise EvidenceGateRefuse(
            "worker_handoff.record present requires bound=true",
            refuse_class=RefuseClass.WORKER_HANDOFF,
        )
    return dict(raw)
