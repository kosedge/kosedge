"""Custodian-ready AC-6 bundle: hash-chained JSONL + SHA256SUMS last.

Plain append without a chain is not a close of the immutability gap.
Every snapshot / forecast / alert write goes through this store.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.evidence import (
    GENESIS_PREV,
    LOG_FILENAME,
    SUMS_FILENAME,
    append_evidence_entry,
    entry_sha,
    verify_evidence_chain,
    write_sha256sums,
)
from src.services.nfl_w8_capture.redact import redact_secrets

SNAPSHOTS_NAME = "snapshots.jsonl"
ALERTS_NAME = "alerts.jsonl"
CREDITS_NAME = "credits.jsonl"
PROVENANCE_NAME = "provenance.jsonl"
MANIFEST_NAME = "MANIFEST.json"
FORECASTS_MKT = Path("forecasts") / "s_mkt"
FORECASTS_IND = Path("forecasts") / "s_ind"
P_EVIDENCE_DIR = Path("p_evidence")


class StoreImmutabilityError(RuntimeError):
    pass


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _last_chained_sha(path: Path) -> str:
    if not path.exists():
        return GENESIS_PREV
    last = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    if not last:
        return GENESIS_PREV
    stored = str(json.loads(last).get("entry_sha") or "")
    if not stored:
        raise StoreImmutabilityError(f"{path.name} last line missing entry_sha")
    return stored


class BundleStore:
    """Append-only hash-chained evidence layout."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def evidence_path(self) -> Path:
        return self.root / LOG_FILENAME

    def sums_path(self) -> Path:
        return self.root / SUMS_FILENAME

    def snapshots_path(self) -> Path:
        return self.root / SNAPSHOTS_NAME

    def refresh_sha256sums(self) -> Path:
        artifacts: list[tuple[str, str]] = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            if path.name == SUMS_FILENAME:
                continue
            rel = path.relative_to(self.root).as_posix()
            artifacts.append((_file_sha256(path), rel))
        return write_sha256sums(self.root, artifacts)

    def verify(self) -> dict[str, Any]:
        chain = verify_evidence_chain(self.root)
        self._verify_chained_jsonl(self.snapshots_path())
        for name in (ALERTS_NAME, CREDITS_NAME, PROVENANCE_NAME):
            path = self.root / name
            if path.exists():
                self._verify_chained_jsonl(path)
        return chain

    def _verify_chained_jsonl(self, path: Path) -> None:
        if not path.exists():
            return
        expected = GENESIS_PREV
        for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not raw.strip():
                continue
            entry = json.loads(raw)
            stored = str(entry.get("entry_sha") or "")
            recomputed = entry_sha({k: v for k, v in entry.items() if k != "entry_sha"})
            if stored != recomputed:
                raise StoreImmutabilityError(f"{path.name} line {index}: entry_sha mismatch")
            if str(entry.get("prev_entry_sha") or "") != expected:
                raise StoreImmutabilityError(f"{path.name} line {index}: prev_entry_sha break")
            expected = stored

    def write_new_file(
        self,
        relpath: str,
        payload: Mapping[str, Any] | bytes,
        *,
        actor: str,
        note: str,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        path = self.root / relpath
        if path.exists():
            raise StoreImmutabilityError(f"refuse overwrite of {relpath}")
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, (bytes, bytearray)):
            data = bytes(payload)
        else:
            data = (_canonical(redact_secrets(dict(payload))) + "\n").encode("utf-8")
        path.write_bytes(data)
        artifact_sha = hashlib.sha256(data).hexdigest()
        entry = append_evidence_entry(
            self.root,
            actor=actor,
            artifact_sha=artifact_sha,
            note=note,
            extra={"relpath": relpath, **dict(extra or {})},
        )
        self.refresh_sha256sums()
        return {"relpath": relpath, "artifact_sha": artifact_sha, "evidence": entry}

    def append_chained_jsonl(
        self,
        relpath: str,
        record: Mapping[str, Any],
        *,
        actor: str,
        note: str,
    ) -> dict[str, Any]:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        body = redact_secrets(dict(record))
        chained = {
            "prev_entry_sha": _last_chained_sha(path),
            "record": body,
        }
        chained["entry_sha"] = entry_sha({k: v for k, v in chained.items() if k != "entry_sha"})
        line = _canonical(chained) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        artifact_sha = hashlib.sha256(line.encode("utf-8")).hexdigest()
        entry = append_evidence_entry(
            self.root,
            actor=actor,
            artifact_sha=artifact_sha,
            note=note,
            extra={"relpath": relpath, "line_entry_sha": chained["entry_sha"]},
        )
        self.refresh_sha256sums()
        return {
            "relpath": relpath,
            "artifact_sha": artifact_sha,
            "entry_sha": chained["entry_sha"],
            "record": chained,
            "evidence": entry,
        }

    def write_manifest(self, manifest: Mapping[str, Any], *, actor: str = "cursor") -> dict[str, Any]:
        path = self.root / MANIFEST_NAME
        if path.exists():
            path.unlink()  # manifest is the one replaceable index; history lives in the chain
        return self.write_new_file(
            MANIFEST_NAME,
            dict(manifest),
            actor=actor,
            note="manifest",
        )
