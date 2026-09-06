"""Path B staging → verify → atomic promote helpers (Phase 2.6F CR3).

Never unlinks or overwrites the live seal before successful verification.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ncaam_lab.holdout_2425.locked_identity import locked_expected_hashes


class PromoteVerificationError(RuntimeError):
    """Staging artifacts failed locked-hash verification; live package untouched."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_payload_sha256(seal: Mapping[str, Any]) -> str:
    body = {
        k: v
        for k, v in seal.items()
        if k
        not in {
            "seal_payload_sha256",
            "seal_receipt_sha256",
            "seal_file_sha256",
            "seal_file_sha256_external",
        }
    }
    text = json.dumps(body, indent=2, sort_keys=True, default=str) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_staging_hashes(
    *,
    staging_root: Path,
    staging_pack_path: Path,
) -> Dict[str, str]:
    """Read staged pack/manifest/seal artifacts and compute identity hashes."""
    feature_manifest = json.loads(
        (staging_root / "feature_package" / "feature_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    label_manifest = json.loads(
        (staging_root / "label_package" / "label_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    seal_path = staging_root / "seal" / "seal_receipt.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal_file_sha = sha256_file(seal_path)
    sidecar = staging_root / "seal" / "seal_receipt.file_sha256"
    if sidecar.exists():
        side = sidecar.read_text(encoding="utf-8").strip().split()[0]
        if side != seal_file_sha:
            raise PromoteVerificationError(
                f"staging seal file sidecar mismatch side={side} file={seal_file_sha}"
            )
    payload_actual = seal_payload_sha256(seal)
    payload_claimed = seal.get("seal_payload_sha256")
    if payload_claimed != payload_actual:
        raise PromoteVerificationError(
            f"staging seal payload mismatch claimed={payload_claimed} actual={payload_actual}"
        )
    return {
        "feature_content_sha256": str(feature_manifest.get("content_sha256") or ""),
        "label_content_sha256": str(label_manifest.get("content_sha256") or ""),
        "feature_manifest_sha256": sha256_file(
            staging_root / "feature_package" / "feature_manifest.json"
        ),
        "label_manifest_sha256": sha256_file(
            staging_root / "label_package" / "label_manifest.json"
        ),
        "seal_payload_sha256": str(payload_claimed or ""),
        "seal_file_sha256": seal_file_sha,
        "canonical_pack_sha256": sha256_file(staging_pack_path),
        "rejected_sha256": str(seal.get("rejected_sha256") or ""),
    }


def verify_against_locked(
    actual: Mapping[str, str],
    *,
    expected: Optional[Mapping[str, str]] = None,
    require_keys: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Compare actual hashes to locked expectations. Raises on mismatch."""
    exp = dict(expected or locked_expected_hashes())
    keys = list(require_keys) if require_keys is not None else list(exp.keys())
    mismatches: List[Dict[str, str]] = []
    for key in keys:
        want = exp.get(key)
        got = actual.get(key)
        if want is None:
            continue
        if got != want:
            mismatches.append({"key": key, "expected": str(want), "actual": str(got)})
    if mismatches:
        raise PromoteVerificationError(
            "staging hashes do not match locked v1.1 expectations: "
            + json.dumps(mismatches)
        )
    return {"ok": True, "checked": keys, "hashes": dict(actual)}


def atomic_replace_file(src: Path, dest: Path) -> None:
    """Atomically replace dest with src (same filesystem). Never unlink dest first."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)


def promote_tree_files(staging_dir: Path, live_dir: Path) -> List[str]:
    """Promote all files under staging_dir into live_dir via os.replace."""
    promoted: List[str] = []
    if not staging_dir.exists():
        return promoted
    for src in sorted(staging_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(staging_dir)
        dest = live_dir / rel
        atomic_replace_file(src, dest)
        promoted.append(str(rel))
    return promoted


def promote_staging_to_live(
    *,
    staging_root: Path,
    staging_pack_path: Path,
    live_root: Path,
    live_pack_path: Path,
    live_seal_dir: Path,
) -> Dict[str, Any]:
    """Promote verified staging artifacts. Seal is promoted last.

    Live seal is never unlinked before this call; os.replace overwrites atomically.
    """
    receipt: Dict[str, Any] = {"promoted": [], "seal_promoted_last": True}
    # Non-seal package dirs first.
    for name in (
        "feature_package",
        "label_package",
        "rejected",
        "schedule_sot",
        "venue",
        "kenpom_audit",
        "odds_audit",
        "quarantine",
    ):
        staging_dir = staging_root / name
        if staging_dir.exists():
            promoted = promote_tree_files(staging_dir, live_root / name)
            receipt["promoted"].append({"dir": name, "files": promoted})

    for name in ("build_summary.json", "readiness_report.json"):
        src = staging_root / name
        if src.exists():
            atomic_replace_file(src, live_root / name)
            receipt["promoted"].append({"file": name})

    if staging_pack_path.exists():
        atomic_replace_file(staging_pack_path, live_pack_path)
        receipt["promoted"].append({"file": str(live_pack_path)})

    # Seal last — live seal untouched until this point.
    seal_staging = staging_root / "seal"
    if seal_staging.exists():
        promoted = promote_tree_files(seal_staging, live_seal_dir)
        receipt["promoted"].append({"dir": "seal", "files": promoted})
    return receipt


def cleanup_staging(staging_root: Path, staging_pack_path: Optional[Path] = None) -> None:
    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    if staging_pack_path is not None and staging_pack_path.exists():
        try:
            staging_pack_path.unlink()
        except OSError:
            pass
