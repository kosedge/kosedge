"""Workspace snapshot for a handoff record. Read-only. No env/secret files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .hashutil import hash_file_list, sha256_file
from .types import WorkerReleaseRefuse

_ENV_NAME_MARKERS = (".env", "credentials", "secret", "token", ".pem", "id_rsa")


def _looks_like_secret_path(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in _ENV_NAME_MARKERS)


def run_git(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise WorkerReleaseRefuse(f"git unavailable: {exc}", code="PLATFORM_LIMITATION") from exc
    if proc.returncode != 0:
        raise WorkerReleaseRefuse(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}",
            code="GIT",
        )
    return proc.stdout


def snapshot_git(root: Path) -> dict[str, Any]:
    repo = Path(root)
    branch = run_git(repo, "branch", "--show-current").strip()
    head = run_git(repo, "rev-parse", "HEAD").strip()
    porcelain = run_git(repo, "status", "--porcelain")
    changed: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if _looks_like_secret_path(path):
            continue
        if line.startswith("??"):
            untracked.append(path)
        else:
            changed.append(path)
    return {
        "branch": branch,
        "head": head,
        "dirty": {
            "clean": not changed and not untracked,
            "changed_paths": changed,
            "preserved": True,
        },
        "untracked": untracked,
    }


def snapshot_processes(pids: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Report-only process list. Never kills. Injected list preferred."""
    if pids is not None:
        return [dict(row) for row in pids]
    return []


def hash_saved_artifacts(root: Path, paths: list[Path]) -> list[dict[str, str]]:
    safe = [Path(p) for p in paths if not _looks_like_secret_path(str(p))]
    hashed = hash_file_list(root, safe)
    return hashed["files"]


def hash_one(path: Path) -> str:
    return sha256_file(path)
