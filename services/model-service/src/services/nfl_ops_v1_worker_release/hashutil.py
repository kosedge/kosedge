"""Canonical JSON + exclusive-write helpers reused from draft #700 / #701.

Source pins (utility only; this module does not import nfl_t5107u and
does not run inherited real-outcome tests):

- canonical_json / sha256_file / write_exclusive / replace_atomic
  from ``nfl_t5107u/one_run.py`` @ 9d436eb1 (#700)
- sha256_text / repo_relative_posix / hash_file_list
  from ``nfl_t5107u/verify_integrate.py`` @ 9d436eb1 (#700)
- exclusive ``*.claim.<bind>`` sidecar naming from #700 / #701 one-run

CERT=0. Synthetic-only consumers. No secrets. No process kill. No draft delete.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


HASH_EXCLUDE_KEYS = frozenset({"content_hash", "checksum_sha256"})


class WorkerReleaseHashError(ValueError):
    """Fail-closed hash / exclusive-write error."""


def canonical_json(payload: Mapping[str, Any] | Sequence[Any] | Any) -> str:
    """Stable JSON used for content hashes. Matches #700 ``_canonical``."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_canonical(payload: Mapping[str, Any]) -> str:
    """Hash a mapping after stripping self-hash fields (same idea as #700)."""
    if not isinstance(payload, Mapping):
        raise WorkerReleaseHashError("sha256_canonical requires a mapping")
    body = {k: v for k, v in payload.items() if k not in HASH_EXCLUDE_KEYS}
    return sha256_text(canonical_json(body))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_relative_posix(root: Path, path: Path) -> str:
    resolved_root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise WorkerReleaseHashError(f"path escapes repo root: {path}") from exc


def hash_file_list(root: Path, paths: Sequence[Path]) -> dict[str, Any]:
    """Repo-relative POSIX paths + per-file sha256. Reproducible across roots."""
    files: list[dict[str, str]] = []
    for path in paths:
        if not Path(path).is_file():
            continue
        files.append(
            {"path": repo_relative_posix(root, path), "sha256": sha256_file(path)}
        )
    files.sort(key=lambda row: row["path"])
    digest = sha256_text(canonical_json(files))
    return {"sha256": digest, "files": files}


def write_exclusive(dest: Path, text: str) -> None:
    """O_CREAT|O_EXCL create. Cleans up only the file we just created on write fail."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    created = False
    try:
        fd = os.open(str(dest), flags, 0o644)
        created = True
    except FileExistsError as exc:
        raise WorkerReleaseHashError(
            "exclusive create refused — file exists"
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        if created:
            try:
                dest.unlink()
            except OSError:
                pass
        raise


def replace_atomic(dest: Path, text: str) -> None:
    tmp = dest.with_name(dest.name + f".{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dest)


def claim_sidecar_path(dest: Path, bind_id: str) -> Path:
    """#700 / #701 naming: ``<record>.claim.<bind_id>``."""
    if not bind_id or any(ch in bind_id for ch in ("/", "\\", "..")):
        raise WorkerReleaseHashError("claim bind_id unsafe")
    return dest.with_name(f"{dest.name}.claim.{bind_id}")
