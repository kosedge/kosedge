"""Bound execution context. Checked before every reader/model call. CERT=0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_r7_correctness_v1.produce import consume_effective_config, r7_code_hash, r7_config_hash
from src.services.nfl_r7_record_date_retro_c1.pins import (
    CLARIFICATIONS_SHA256,
    IDENTITY_SHA256,
    NOMINAL_SHA256,
    PROFILE,
    REST_META_SHA256,
    SPEC_SHA256,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse


def context_hash(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def bind_execution_context(
    *,
    root: Path,
    channel: str,
    cohort: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = consume_effective_config()
    body = {
        "channel": channel,
        "profile": PROFILE,
        "code_hash": r7_code_hash(root),
        "config_hash": r7_config_hash(cfg),
        "spec_sha256": SPEC_SHA256,
        "clarifications_sha256": CLARIFICATIONS_SHA256,
        "identity_sha256": IDENTITY_SHA256,
        "nominal_sha256": NOMINAL_SHA256,
        "rest_meta_sha256": REST_META_SHA256,
        "source_roles": {
            "spec": "BOUND",
            "identity": "BOUND_COLUMNS_ONLY",
            "nominal": "BOUND_METADATA",
            "rest_meta": "BOUND_METADATA",
            "outcomes": "UNOPENED",
            "games": "UNOPENED",
        },
        "cohort": dict(cohort),
    }
    if extra:
        body["extra"] = dict(extra)
    digest = context_hash(body)
    body["context_hash"] = digest
    return body


def require_context(bound: Mapping[str, Any], expected_hash: str, *, reader_role: str) -> None:
    if not expected_hash or bound.get("context_hash") != expected_hash:
        raise RetroRefuse(f"{reader_role} refused: context hash mismatch")
    recomputed = context_hash({k: v for k, v in bound.items() if k != "context_hash"})
    if recomputed != expected_hash:
        raise RetroRefuse(f"{reader_role} refused: context rehash drifted")
