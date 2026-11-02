"""Immutable timestamped snapshots via the AC-6 hash-chained store."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_w8_capture.redact import redact_secrets
from src.services.nfl_w8_capture.store import SNAPSHOTS_NAME, BundleStore, _canonical

SNAPSHOT_FILENAME = SNAPSHOTS_NAME


class SnapshotImmutabilityError(RuntimeError):
    pass


def snapshot_content_sha(payload: Mapping[str, Any]) -> str:
    from hashlib import sha256

    return sha256(_canonical(redact_secrets(dict(payload))).encode("utf-8")).hexdigest()


def append_snapshot(
    lake_dir: str | Path,
    payload: Mapping[str, Any],
    *,
    captured_at: datetime | None = None,
    actor: str = "nfl_w8_capture",
) -> dict[str, Any]:
    """Append one chained snapshot + evidence entry + SHA256SUMS refresh."""
    stamp = captured_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    cleaned = redact_secrets(dict(payload))
    record = {
        "captured_at": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": cleaned,
        "content_sha256": snapshot_content_sha(cleaned),
    }
    store = BundleStore(lake_dir)
    committed = store.append_chained_jsonl(
        SNAPSHOTS_NAME,
        record,
        actor=actor,
        note="snapshot",
    )
    out = dict(record)
    out["entry_sha"] = committed["entry_sha"]
    out["prev_entry_sha"] = committed["record"]["prev_entry_sha"]
    return out
