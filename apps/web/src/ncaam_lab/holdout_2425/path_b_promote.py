"""Path B staging → verify → release-pointer promote (Phase 2.6F CR5).

Live authority is a single CURRENT pointer (symlink) to an immutable release
directory. Materialize the full release first; only then atomically switch the
pointer. Mid-materialize failures leave CURRENT (and therefore all live
artifacts) unchanged.

Never describe multi-file os.replace of live paths as "atomic".
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ncaam_lab.holdout_2425.locked_identity import locked_expected_hashes

CURRENT_POINTER_NAME = "CURRENT"
RELEASES_DIRNAME = "releases"

# Package dirs copied into each immutable release.
PROMOTE_PACKAGE_DIRS = (
    "feature_package",
    "label_package",
    "rejected",
    "schedule_sot",
    "venue",
    "kenpom_audit",
    "odds_audit",
    "quarantine",
    "seal",
    "inventory",
)
PROMOTE_ROOT_FILES = ("build_summary.json", "readiness_report.json")

# Compat publish targets under live_root that should track CURRENT after switch.
COMPAT_LIVE_DIRS = (
    "feature_package",
    "label_package",
    "rejected",
    "seal",
)


class PromoteVerificationError(RuntimeError):
    """Staging artifacts failed locked-hash verification; live package untouched."""


class PromoteError(RuntimeError):
    """Release materialize or pointer switch failed; live CURRENT unchanged."""


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


def current_pointer_path(live_root: Path) -> Path:
    return live_root / CURRENT_POINTER_NAME


def resolve_current_release(live_root: Path) -> Optional[Path]:
    """Return the resolved CURRENT release directory, or None if unset."""
    cur = current_pointer_path(live_root)
    if cur.is_symlink() or cur.exists():
        return cur.resolve()
    return None


def resolve_live_artifacts(
    *,
    live_root: Path,
    live_pack_path: Path,
    live_seal_dir: Path,
) -> Dict[str, Path]:
    """Authoritative live artifact paths (CURRENT release when present)."""
    release = resolve_current_release(live_root)
    if release is not None:
        pack_name = live_pack_path.name
        return {
            "release_dir": release,
            "seal_dir": release / "seal",
            "pack_path": release / pack_name,
            "feature_package": release / "feature_package",
            "label_package": release / "label_package",
            "rejected": release / "rejected",
            "feature_content": release / "feature_package" / "features.json",
            "feature_manifest": release
            / "feature_package"
            / "feature_manifest.json",
            "label_content": release / "label_package" / "labels.json",
            "label_manifest": release / "label_package" / "label_manifest.json",
            "rejected_events": release / "rejected" / "rejected_events.json",
            "seal_receipt": release / "seal" / "seal_receipt.json",
            "seal_sidecar": release / "seal" / "seal_receipt.file_sha256",
        }
    return {
        "release_dir": live_root,
        "seal_dir": live_seal_dir,
        "pack_path": live_pack_path,
        "feature_package": live_root / "feature_package",
        "label_package": live_root / "label_package",
        "rejected": live_root / "rejected",
        "feature_content": live_root / "feature_package" / "features.json",
        "feature_manifest": live_root / "feature_package" / "feature_manifest.json",
        "label_content": live_root / "label_package" / "labels.json",
        "label_manifest": live_root / "label_package" / "label_manifest.json",
        "rejected_events": live_root / "rejected" / "rejected_events.json",
        "seal_receipt": live_seal_dir / "seal_receipt.json",
        "seal_sidecar": live_seal_dir / "seal_receipt.file_sha256",
    }


def _maybe_fail(fail_at: Optional[str], boundary: str) -> None:
    if fail_at and fail_at == boundary:
        if boundary == "during_pointer_switch":
            raise OSError(errno_placeholder(), f"injected OSError at {boundary}")
        raise PromoteError(f"injected promote failure at boundary={boundary}")


def errno_placeholder() -> int:
    return getattr(os, "EIO", 5)


def _atomic_switch_symlink(link_path: Path, target: Path) -> None:
    """Atomically point link_path at target via temp symlink + os.replace.

    This is the only live-cutover step. On POSIX, replacing a symlink is a
    single rename and does not tear the previous release.
    """
    link_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        rel_target = os.path.relpath(target, start=link_path.parent)
    except ValueError:
        rel_target = str(target)
    tmp = link_path.parent / f".{link_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    if tmp.exists() or tmp.is_symlink():
        tmp.unlink()
    try:
        tmp.symlink_to(rel_target)
        os.replace(tmp, link_path)
    except OSError:
        if tmp.exists() or tmp.is_symlink():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _replace_path_with_symlink(path: Path, target: Path) -> None:
    """Publish a compatibility symlink at path → target (post-CURRENT only).

    Not the live cutover. CURRENT is already switched; failures here do not
    roll back the release pointer.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        rel_target = os.path.relpath(target, start=path.parent)
    except ValueError:
        rel_target = str(target)

    if path.is_symlink():
        tmp = path.parent / f".{path.name}.pubtmp.{uuid.uuid4().hex[:8]}"
        if tmp.exists() or tmp.is_symlink():
            tmp.unlink()
        tmp.symlink_to(rel_target)
        os.replace(tmp, path)
        return

    if path.exists():
        aside = path.parent / f".{path.name}.pre_pointer_{uuid.uuid4().hex[:8]}"
        os.rename(path, aside)

    tmp = path.parent / f".{path.name}.pubtmp.{uuid.uuid4().hex[:8]}"
    if tmp.exists() or tmp.is_symlink():
        tmp.unlink()
    tmp.symlink_to(rel_target)
    os.replace(tmp, path)


def materialize_release_tree(
    *,
    staging_root: Path,
    staging_pack_path: Path,
    release_dir: Path,
    pack_basename: str,
    fail_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Copy staging into a new immutable release directory (not yet live)."""
    if release_dir.exists():
        raise PromoteError(f"release directory already exists: {release_dir}")
    release_dir.mkdir(parents=True, exist_ok=False)
    receipt: Dict[str, Any] = {"release_dir": str(release_dir), "copied": []}

    try:
        for name in PROMOTE_PACKAGE_DIRS:
            staging_dir = staging_root / name
            if not staging_dir.exists():
                continue
            _maybe_fail(fail_at, f"before_dir:{name}")
            dest = release_dir / name
            shutil.copytree(staging_dir, dest, symlinks=False)
            receipt["copied"].append({"dir": name})
            _maybe_fail(fail_at, f"after_dir:{name}")

        for name in PROMOTE_ROOT_FILES:
            src = staging_root / name
            if not src.exists():
                continue
            _maybe_fail(fail_at, f"before_file:{name}")
            dest = release_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            receipt["copied"].append({"file": name})
            _maybe_fail(fail_at, f"after_file:{name}")

        if staging_pack_path.exists():
            _maybe_fail(fail_at, "before_pack")
            dest_pack = release_dir / pack_basename
            shutil.copy2(staging_pack_path, dest_pack)
            receipt["copied"].append({"file": pack_basename})
            _maybe_fail(fail_at, "after_pack")

        _maybe_fail(fail_at, "after_materialize")
    except (OSError, PromoteError):
        # Incomplete release must never become CURRENT. Best-effort cleanup.
        if release_dir.exists():
            shutil.rmtree(release_dir, ignore_errors=True)
        raise

    return receipt


def promote_staging_to_live(
    *,
    staging_root: Path,
    staging_pack_path: Path,
    live_root: Path,
    live_pack_path: Path,
    live_seal_dir: Path,
    fail_at: Optional[str] = None,
    release_id: Optional[str] = None,
    publish_compat_symlinks: bool = True,
) -> Dict[str, Any]:
    """Promote verified staging via immutable release + atomic CURRENT pointer.

    1. Materialize a complete release under live_root/releases/<id>/
    2. After full materialize, atomically switch live_root/CURRENT → that release
    3. Optionally publish compatibility symlinks at traditional live paths

    Step 1 failures leave CURRENT unchanged (all prior live artifacts intact).
    Step 2 is a single symlink rename. Multi-file live os.replace is not used
    and must not be called atomic.
    """
    rid = release_id or f"r-{time.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:10]}"
    releases_root = live_root / RELEASES_DIRNAME
    releases_root.mkdir(parents=True, exist_ok=True)
    release_dir = releases_root / rid
    pack_basename = live_pack_path.name

    materialize_receipt = materialize_release_tree(
        staging_root=staging_root,
        staging_pack_path=staging_pack_path,
        release_dir=release_dir,
        pack_basename=pack_basename,
        fail_at=fail_at,
    )

    _maybe_fail(fail_at, "before_pointer_switch")
    _maybe_fail(fail_at, "during_pointer_switch")

    pointer = current_pointer_path(live_root)
    try:
        _atomic_switch_symlink(pointer, release_dir)
    except OSError as exc:
        # Pointer unchanged (or never created). Drop incomplete? Release is
        # complete but unpublished — safe to leave for inspection; live intact.
        raise PromoteError(
            f"CURRENT pointer switch failed; live release unchanged: {exc}"
        ) from exc

    receipt: Dict[str, Any] = {
        "promotion_model": "immutable_release_plus_current_pointer",
        "atomic_unit": "CURRENT_symlink_os_replace",
        "multi_file_live_replace_called_atomic": False,
        "release_id": rid,
        "release_dir": str(release_dir),
        "current_pointer": str(pointer),
        "materialize": materialize_receipt,
        "seal_promoted_last": False,  # entire release flips together via pointer
        "promoted": [{"release": rid, "via": "CURRENT_pointer"}],
    }

    if publish_compat_symlinks:
        # Post-cutover only: traditional paths track CURRENT. Not the atomic unit.
        current = pointer  # relative symlink; targets resolve via CURRENT
        for name in COMPAT_LIVE_DIRS:
            src_in_release = release_dir / name
            if not src_in_release.exists():
                continue
            dest = live_root / name
            # Point at CURRENT/<name> so future pointer switches stay coherent.
            _replace_path_with_symlink(dest, current / name)
            receipt.setdefault("compat_symlinks", []).append(name)
        # Pack may live outside live_root (model-service path) or under it.
        pack_in_release = release_dir / pack_basename
        if pack_in_release.exists():
            _replace_path_with_symlink(live_pack_path, current / pack_basename)
            receipt.setdefault("compat_symlinks", []).append(str(live_pack_path))
        # If caller passed a seal_dir that is not live_root/seal, publish too.
        if live_seal_dir.resolve() != (live_root / "seal").resolve():
            if (release_dir / "seal").exists():
                _replace_path_with_symlink(live_seal_dir, current / "seal")
                receipt.setdefault("compat_symlinks", []).append(str(live_seal_dir))

    receipt["current_release_resolved"] = str(pointer.resolve())
    return receipt


def cleanup_staging(staging_root: Path, staging_pack_path: Optional[Path] = None) -> None:
    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    if staging_pack_path is not None and staging_pack_path.exists():
        try:
            staging_pack_path.unlink()
        except OSError:
            pass


# Back-compat aliases — do not use for new live cutovers.
def atomic_replace_file(src: Path, dest: Path) -> None:
    """Single-file replace helper (NOT a multi-artifact live promote)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)


def promote_tree_files(staging_dir: Path, live_dir: Path) -> List[str]:
    """Deprecated multi-file replace — retained only for non-live utilities.

    Must not be used as the live package cutover (not atomic across files).
    """
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
