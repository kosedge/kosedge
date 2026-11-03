"""Hash / path helpers.

Reused from #700 tip 9d436eb1 ``verify_integrate.sha256_text`` /
``hash_file_list`` / ``repo_relative_posix`` and #700 ``manifest.sha256_bytes``.
#701 tip 455a8e43 carries the same helpers on verify_integrate.
Does not import nfl_t5107u (real-outcome tests stay unrun).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.services.nfl_hhl1_capture.identity import canonical_json, is_sha256_hex, sha256_hex
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_relative_posix(root: Path, path: Path) -> str:
    resolved_root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise EvidenceGateRefuse(
            f"path escapes repo root: {path}",
            refuse_class=RefuseClass.WRITE_TAMPER,
        ) from exc


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
    digest = sha256_text(json.dumps(files, separators=(",", ":"), sort_keys=True))
    return {"sha256": digest, "files": files}


def require_sha256_hex(value: Any, name: str) -> str:
    if not is_sha256_hex(value):
        raise EvidenceGateRefuse(
            f"{name} must be sha256 hex (got {value!r})",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    return str(value)


__all__ = [
    "canonical_json",
    "hash_file_list",
    "is_sha256_hex",
    "repo_relative_posix",
    "require_sha256_hex",
    "sha256_bytes",
    "sha256_file",
    "sha256_hex",
    "sha256_text",
]
