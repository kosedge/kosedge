"""NFL_OPS_V1 worker final-state / release / claim record (Primary B).

States: WRITING → HANDOFF_RECORDED → QUIESCENT → RELEASE_CONFIRMED → CLAIMED_BY_SUCCESSOR.

Plugs into Primary A's evidence-manifest via ``as_worker_handoff()``
(field name ``worker_handoff``). Stable keys + content_hash.

CERT=0. Synthetic only. Mocked release ≠ platform reclaim.
Missing capability → PLATFORM_LIMITATION, never invented PASS.
"""

from .claim import claim_successor, load_record, persist_new_record
from .hashutil import (
    canonical_json,
    claim_sidecar_path,
    hash_file_list,
    sha256_canonical,
    sha256_file,
    sha256_text,
    write_exclusive,
)
from .platform import (
    CursorCloudReclaimAdapter,
    MockedReclaimAdapter,
    PlatformProbe,
    SyntheticInProcessReleaseAdapter,
    default_adapter,
)
from .record import (
    as_worker_handoff,
    bind_id_for,
    build_record,
    content_hash_of,
    serialize_record,
    stamp_content_hash,
    validate_record,
    with_fields,
)
from .snapshot import hash_saved_artifacts, snapshot_git, snapshot_processes
from .state import (
    attach_successor,
    confirm_release,
    mark_quiescent,
    record_handoff,
    stamp_platform_limitation,
)
from .types import (
    CERT,
    SCHEMA_ID,
    SCHEMA_VERSION,
    WORKER_HANDOFF_FIELD,
    WORKER_HANDOFF_KEYS,
    WorkerReleaseRefuse,
)

__all__ = [
    "CERT",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "WORKER_HANDOFF_FIELD",
    "WORKER_HANDOFF_KEYS",
    "CursorCloudReclaimAdapter",
    "MockedReclaimAdapter",
    "PlatformProbe",
    "SyntheticInProcessReleaseAdapter",
    "WorkerReleaseRefuse",
    "as_worker_handoff",
    "attach_successor",
    "bind_id_for",
    "build_record",
    "canonical_json",
    "claim_sidecar_path",
    "claim_successor",
    "confirm_release",
    "content_hash_of",
    "default_adapter",
    "hash_file_list",
    "hash_saved_artifacts",
    "load_record",
    "mark_quiescent",
    "persist_new_record",
    "record_handoff",
    "serialize_record",
    "sha256_canonical",
    "sha256_file",
    "sha256_text",
    "snapshot_git",
    "snapshot_processes",
    "stamp_content_hash",
    "stamp_platform_limitation",
    "validate_record",
    "with_fields",
    "write_exclusive",
]
