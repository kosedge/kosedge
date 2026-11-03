"""Constants and refuse codes for the NFL_OPS_V1 worker release/claim record.

Stable serializable contract for Primary A's ``worker_handoff`` field.
CERT=0. Synthetic only. Passing checks are not self-acceptance.
"""

from __future__ import annotations

from typing import Any

SCHEMA_ID = "nfl-ops-v1-worker-release-claim-v1"
SCHEMA_VERSION = 1
WORKER_HANDOFF_FIELD = "worker_handoff"
CERT = 0

PROTOCOL_NAME = "NFL_OPS_V1"
PROTOCOL_HASH = "ed10e80f"
OWNER_CLEAR = "f1fb6735"
SCOPE_ID = "chief-nflgreen-overnight-ops-20261102-0330"

STATE_WRITING = "WRITING"
STATE_HANDOFF_RECORDED = "HANDOFF_RECORDED"
STATE_QUIESCENT = "QUIESCENT"
STATE_RELEASE_CONFIRMED = "RELEASE_CONFIRMED"
STATE_CLAIMED = "CLAIMED_BY_SUCCESSOR"

STATES = (
    STATE_WRITING,
    STATE_HANDOFF_RECORDED,
    STATE_QUIESCENT,
    STATE_RELEASE_CONFIRMED,
    STATE_CLAIMED,
)

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    STATE_WRITING: frozenset({STATE_HANDOFF_RECORDED}),
    STATE_HANDOFF_RECORDED: frozenset({STATE_QUIESCENT}),
    STATE_QUIESCENT: frozenset({STATE_RELEASE_CONFIRMED}),
    STATE_RELEASE_CONFIRMED: frozenset({STATE_CLAIMED}),
    STATE_CLAIMED: frozenset(),
}

EVIDENCE_EXECUTED_HERE = "EXECUTED_HERE"
EVIDENCE_INDEPENDENT = "INDEPENDENT_EXECUTION"
EVIDENCE_SOURCE_INSPECTION = "SOURCE_INSPECTION"
EVIDENCE_REPORTED_ONLY = "REPORTED_ONLY"
EVIDENCE_NOT_RUN = "NOT_RUN"

EVIDENCE_LABELS = (
    EVIDENCE_EXECUTED_HERE,
    EVIDENCE_INDEPENDENT,
    EVIDENCE_SOURCE_INSPECTION,
    EVIDENCE_REPORTED_ONLY,
    EVIDENCE_NOT_RUN,
)

RELEASE_NOT_RELEASED = "NOT_RELEASED"
RELEASE_PLATFORM_LIMITATION = "PLATFORM_LIMITATION"
RELEASE_SYNTHETIC = "SYNTHETIC_PLATFORM_RELEASE"
RELEASE_CONFIRMED_KIND = "PLATFORM_RELEASE_CONFIRMED"

RELEASE_KINDS = (
    RELEASE_NOT_RELEASED,
    RELEASE_PLATFORM_LIMITATION,
    RELEASE_SYNTHETIC,
    RELEASE_CONFIRMED_KIND,
)

CAPABILITY_ABSENT = "ABSENT"
CAPABILITY_PRESENT = "PRESENT"
CAPABILITY_UNKNOWN = "UNKNOWN"

CURSOR_RECLAIM_CAPABILITY_ID = "cursor_cloud_workspace_reclaim"
SYNTHETIC_BOARD_CAPABILITY_ID = "synthetic_inprocess_release_board"
MOCKED_CAPABILITY_ID = "mocked_workspace_reclaim"

# Top-level keys. Unknown extras are refused (no invented extension channel).
REQUIRED_TOP_LEVEL = (
    "schema",
    "schema_version",
    "cert",
    "synthetic",
    "self_accept",
    "scope_id",
    "protocol",
    "protocol_hash",
    "owner_clear",
    "task",
    "worker",
    "branch",
    "head",
    "workspace_alias",
    "dirty",
    "untracked",
    "saved_artifacts",
    "log_hashes",
    "tests",
    "limits",
    "active_writer",
    "running_jobs",
    "pending_prompts",
    "successor",
    "release_evidence",
    "state",
    "state_history",
    "content_hash",
)

WORKER_HANDOFF_KEYS = (
    "field",
    "schema",
    "schema_version",
    "content_hash",
    "state",
    "task_id",
    "worker_id",
    "branch",
    "head",
    "workspace_alias",
    "release_kind",
    "evidence_label",
    "platform_capability",
    "mocked_release",
    "not_a_pass",
    "record",
)

FORBIDDEN_CALL_TOKENS = (
    "os.kill",
    "signal.SIGKILL",
    "signal.SIGTERM",
    "shutil.rmtree",
    "os.killpg",
)


class WorkerReleaseRefuse(ValueError):
    """Fail-closed release/claim refuse. Never ACCEPT. Never self-accept."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        record: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or "REFUSE"
        self.record = record
