"""Immutable timestamped append-only snapshots (AC-6). No overwrites."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_w8_capture.redact import redact_secrets

SNAPSHOT_FILENAME = "snapshots.jsonl"


class SnapshotImmutabilityError(RuntimeError):
    pass


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def snapshot_content_sha(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(redact_secrets(dict(payload))).encode("utf-8")).hexdigest()


def append_snapshot(
    lake_dir: str | Path,
    payload: Mapping[str, Any],
    *,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    """Append one snapshot record. Refuses rewrite of an existing file body."""
    path = Path(lake_dir) / SNAPSHOT_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_file():
        raise SnapshotImmutabilityError(f"snapshot path is not a file: {path}")

    stamp = captured_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)

    record = {
        "captured_at": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": redact_secrets(dict(payload)),
    }
    record["content_sha256"] = snapshot_content_sha(record["payload"])
    line = _canonical(record) + "\n"

    # Append-only: open in append mode; never truncate.
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return record
