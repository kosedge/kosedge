"""Append-only hash-chained evidence log (AC-6). SHA256SUMS written last."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.services.nfl_w8_capture.redact import redact_secrets

GENESIS_PREV = "0" * 64
LOG_FILENAME = "evidence.jsonl"
SUMS_FILENAME = "SHA256SUMS"


class EvidenceChainError(RuntimeError):
    pass


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def entry_sha(entry: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _last_entry_sha(path: Path) -> str:
    lines = _read_lines(path)
    if not lines:
        return GENESIS_PREV
    last = json.loads(lines[-1])
    stored = str(last.get("entry_sha") or "")
    if not stored:
        raise EvidenceChainError("last log line missing entry_sha")
    return stored


def append_evidence_entry(
    log_dir: str | Path,
    *,
    actor: str,
    artifact_sha: str,
    note: str = "",
    extra: Optional[Mapping[str, Any]] = None,
    entry_time: Optional[datetime] = None,
) -> dict[str, Any]:
    path = Path(log_dir) / LOG_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = entry_time or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)

    body: dict[str, Any] = {
        "prev_entry_sha": _last_entry_sha(path),
        "entry_time": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "actor": str(actor),
        "artifact_sha": str(artifact_sha),
        "note": str(note),
        "extra": redact_secrets(dict(extra or {})),
    }
    body["entry_sha"] = entry_sha({k: v for k, v in body.items() if k != "entry_sha"})

    with path.open("a", encoding="utf-8") as fh:
        fh.write(_canonical(body) + "\n")
    return body


def verify_evidence_chain(log_dir: str | Path) -> dict[str, Any]:
    path = Path(log_dir) / LOG_FILENAME
    lines = _read_lines(path)
    expected_prev = GENESIS_PREV
    verified = 0
    for index, raw in enumerate(lines):
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvidenceChainError(f"line {index}: invalid json") from exc
        stored = str(entry.get("entry_sha") or "")
        recomputed = entry_sha({k: v for k, v in entry.items() if k != "entry_sha"})
        if stored != recomputed:
            raise EvidenceChainError(f"line {index}: entry_sha mismatch")
        if str(entry.get("prev_entry_sha") or "") != expected_prev:
            raise EvidenceChainError(f"line {index}: prev_entry_sha break")
        expected_prev = stored
        verified += 1
    return {
        "ok": True,
        "entries": verified,
        "head_sha": expected_prev if verified else GENESIS_PREV,
    }


def write_sha256sums(log_dir: str | Path, artifacts: Sequence[tuple[str, str]]) -> Path:
    """Write SHA256SUMS last. ``artifacts`` is (sha256, relative_name)."""
    path = Path(log_dir) / SUMS_FILENAME
    lines = [f"{sha}  {name}\n" for sha, name in artifacts]
    path.write_text("".join(lines), encoding="utf-8")
    return path
