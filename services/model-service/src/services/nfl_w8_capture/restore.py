"""Read-only restore of prior P-evidence deposits. No protected eval."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from src.services.nfl_w8_capture.evidence import SUMS_FILENAME, verify_evidence_chain
from src.services.nfl_w8_capture.store import P_EVIDENCE_DIR, BundleStore


class PEvidenceRestoreError(RuntimeError):
    pass


def restore_p_evidence(
    source: str | Path,
    store: BundleStore,
    *,
    deposit_id: str | None = None,
    actor: str = "nfl_w8_capture",
) -> dict[str, Any]:
    """Copy a verified deposit into ``p_evidence/<id>/``. Read-only. No grading."""
    src = Path(source)
    if not src.is_dir():
        raise PEvidenceRestoreError(f"P-evidence deposit missing: {src}")
    sums = src / SUMS_FILENAME
    if not sums.is_file():
        raise PEvidenceRestoreError("deposit is not custodian-ready (SHA256SUMS missing)")
    chain = verify_evidence_chain(src)
    _verify_sums(src)

    label = deposit_id or src.name
    dest_rel = (P_EVIDENCE_DIR / label).as_posix()
    dest = store.root / dest_rel
    if dest.exists():
        raise PEvidenceRestoreError(f"refuse overwrite of restored deposit {dest_rel}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    for path in dest.rglob("*"):
        if path.is_file():
            path.chmod(0o444)

    listing = sorted(
        p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()
    )
    extra = {
        "deposit_id": label,
        "source": str(src),
        "files": listing,
        "source_head_sha": chain.get("head_sha"),
        "eval": "not_run",
    }
    # Pointer file is the only new writable artifact; deposit bytes stay 0444.
    pointer = store.write_new_file(
        f"{dest_rel}.restored.json",
        extra,
        actor=actor,
        note=f"restore_p_evidence:{label}",
        extra={"deposit_id": label, "eval": "not_run"},
    )
    return {
        "deposit_id": label,
        "dest": dest_rel,
        "files": listing,
        "source_head_sha": chain.get("head_sha"),
        "eval": "not_run",
        "pointer": pointer,
    }


def _verify_sums(root: Path) -> None:
    sums = root / SUMS_FILENAME
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sha, name = line.split("  ", 1)
        path = root / name.strip()
        if not path.is_file():
            raise PEvidenceRestoreError(f"SHA256SUMS missing file: {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != sha.strip():
            raise PEvidenceRestoreError(f"SHA256SUMS mismatch: {name}")
