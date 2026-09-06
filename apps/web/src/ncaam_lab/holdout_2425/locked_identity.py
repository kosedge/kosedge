"""Frozen v1.1 identity timestamps + locked expected hashes (Phase 2.6F CR3).

Operational wall-clock (datetime.now) must not enter hashed pack / manifest / seal
identity. Values below are taken from the sealed v1.1 tip artifacts and verified
against prior receipts — do not invent new timestamps.
"""

from __future__ import annotations

from typing import Dict

# Frozen timestamps embedded in hashed identity (exact v1.1 seal tip).
V1_1_FEATURE_SEALED_AT = "2026-09-05T13:27:18.625322+00:00"
V1_1_LABEL_SEALED_AT = "2026-09-05T13:27:18.625658+00:00"
V1_1_SEAL_SEALED_AT = "2026-09-05T13:27:18.625914+00:00"
# Canonical schedule pack as_of from the locked pack bytes (sha 4016f2ab…).
V1_1_CANONICAL_PACK_AS_OF = "2026-09-05T11:28Z"
# Non-membership artifacts kept deterministic when rebuilding the sealed tree.
V1_1_SCHEDULE_INDEX_BUILT_AT = "2026-09-05T13:27:17.761131+00:00"
V1_1_BUILD_SUMMARY_BUILT_AT = "2026-09-05T13:27:18.631709+00:00"

# Locked expected hashes from sealed v1.1 / schedule_sot_index.manifest / receipts.
LOCKED_FEATURE_CONTENT_SHA256 = (
    "8c9e7ffffd05511e0e90f1e9bbd95d68377370f6a7660f0a4652e50f2d820940"
)
LOCKED_LABEL_CONTENT_SHA256 = (
    "aa7e10887efbb0a6790bc3be3bd0a6ce8c7612afc7e55234ce81993410bfcd12"
)
LOCKED_FEATURE_MANIFEST_SHA256 = (
    "f45c0438e40f62eee12fd6d9ec944ab077f2cb6734cc79db95ce2462c0c7abf9"
)
LOCKED_LABEL_MANIFEST_SHA256 = (
    "0893a9e28ebd1e878a5ef8289540ffd35db864f55c4de4f34bda2bacefb60cc0"
)
LOCKED_SEAL_PAYLOAD_SHA256 = (
    "af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84"
)
LOCKED_SEAL_FILE_SHA256 = (
    "82852e2460bf876d75aae647232860820a998814b4bef76c236bdf058f0ddca2"
)
LOCKED_CANONICAL_PACK_SHA256 = (
    "4016f2ab4dcfbf713fdd005b4468ab5576345bea321caa59333685f224ae828e"
)
LOCKED_REJECTED_SHA256 = (
    "7adad2930c9a0d54c9aa4d6c3072ee7b90637cde9352f4b6699b02fca09b4c3d"
)

# Sealed v1.1 tip content commit (features/labels/rejected/pack bytes). Clean A/B
# strip bulk content from git; CR3(b) recovers these exact bytes from this ref.
# Same tip as origin/cursor/ncaam-2425-sealed-holdout-73d9 and refs/pull/491/head.
SEALED_V1_1_CONTENT_GIT_SHA = "2d51cdcdc0d0d87c185352388f1ea891992b24f3"
SEALED_V1_1_CONTENT_FETCH_REF = "refs/pull/491/head"


def locked_expected_hashes() -> Dict[str, str]:
    return {
        "feature_content_sha256": LOCKED_FEATURE_CONTENT_SHA256,
        "label_content_sha256": LOCKED_LABEL_CONTENT_SHA256,
        "feature_manifest_sha256": LOCKED_FEATURE_MANIFEST_SHA256,
        "label_manifest_sha256": LOCKED_LABEL_MANIFEST_SHA256,
        "seal_payload_sha256": LOCKED_SEAL_PAYLOAD_SHA256,
        "seal_file_sha256": LOCKED_SEAL_FILE_SHA256,
        "canonical_pack_sha256": LOCKED_CANONICAL_PACK_SHA256,
        "rejected_sha256": LOCKED_REJECTED_SHA256,
    }
