"""Exclusive successor claim. Competing / wrong / stale claims are refused.

Uses the #700 / #701 ``O_CREAT|O_EXCL`` sidecar (``<record>.claim.<bind>``).
Does not delete drafts. Does not kill writers. Does not force-take a workspace.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .gates import assert_clean_for_release, assert_successor_named
from .hashutil import (
    WorkerReleaseHashError,
    claim_sidecar_path,
    replace_atomic,
    write_exclusive,
)
from .record import bind_id_for, utc_now, validate_record
from .state import apply_transition
from .types import STATE_RELEASE_CONFIRMED, WorkerReleaseRefuse


def persist_new_record(path: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    current = validate_record(record)
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_exclusive(dest, json.dumps(current, indent=2, sort_keys=True) + "\n")
    except WorkerReleaseHashError as exc:
        raise WorkerReleaseRefuse(
            "record already persisted — refuse overwrite",
            code="COMPETING_CLAIM",
            record=current,
        ) from exc
    return current


def load_record(path: Path) -> dict[str, Any]:
    dest = Path(path)
    if not dest.is_file():
        raise WorkerReleaseRefuse("release record missing", code="MISSING_FIELD")
    return validate_record(json.loads(dest.read_text(encoding="utf-8")))


def claim_successor(
    record: Mapping[str, Any],
    *,
    dest: Path,
    successor_id: str,
    claim_head: str,
    claim_content_hash: str,
    at_utc: str | None = None,
) -> dict[str, Any]:
    current = validate_record(record)
    if current["state"] != STATE_RELEASE_CONFIRMED:
        raise WorkerReleaseRefuse(
            f"claim refused from {current['state']}",
            code="ILLEGAL_TRANSITION",
            record=current,
        )
    assert_clean_for_release(current)
    assert_successor_named(current, successor_id)

    if claim_head != current["head"] or claim_content_hash != current["content_hash"]:
        raise WorkerReleaseRefuse(
            "stale claim — head or content_hash does not match live record",
            code="STALE_CLAIM",
            record=current,
        )

    bind_id = bind_id_for(current, successor_id)
    sidecar = claim_sidecar_path(Path(dest), bind_id)
    payload = {
        "bind_id": bind_id,
        "successor_id": successor_id,
        "head": current["head"],
        "content_hash": current["content_hash"],
        "workspace_alias": current["workspace_alias"],
        "claimed_at_utc": at_utc or utc_now(),
    }
    try:
        write_exclusive(sidecar, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    except WorkerReleaseHashError as exc:
        raise WorkerReleaseRefuse(
            "competing claim refused — already claimed",
            code="COMPETING_CLAIM",
            record=current,
        ) from exc

    nxt = apply_transition(
        current, "CLAIMED_BY_SUCCESSOR", at_utc=at_utc, code="CLAIM"
    )
    replace_atomic(Path(dest), json.dumps(nxt, indent=2, sort_keys=True) + "\n")
    nxt = dict(nxt)
    nxt_out = dict(nxt)
    # sidecar path is operational, not part of the hashed record body
    return validate_record(nxt_out)


__all__ = [
    "claim_successor",
    "load_record",
    "persist_new_record",
]
