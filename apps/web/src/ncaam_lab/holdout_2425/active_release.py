"""Authoritative read API for the active sealed holdout release (CURRENT).

Phase 2.6F CR7 — one shared SoT for governed consumers.

Once ``live_root/CURRENT`` exists, legacy flat constants
(``FEATURE_DIR``, ``LABEL_DIR``, ``SEAL_DIR``, ``CANONICAL_PACK_PATH``, …)
are **non-authoritative**. All governed readers must go through this module
(or ``resolve_live_artifacts`` with the same live_root defaults).

Writers that materialize staging trees still take explicit ``out_root`` /
staging paths; they must not treat flat live constants as post-CURRENT SoT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ncaam_lab.holdout_2425 import constants as C
from ncaam_lab.holdout_2425.path_b_promote import (
    GOVERNED_CONSUMER_KEYS,
    consumer_release_identity,
    resolve_current_release,
    resolve_live_artifacts,
    sha256_file,
)

# Logical artifact keys exposed to consumers (subset of resolve_live_artifacts).
ACTIVE_READ_KEYS = (
    "release_dir",
    "pack_path",
    "feature_package",
    "label_package",
    "rejected",
    "seal_dir",
    "feature_content",
    "feature_manifest",
    "label_content",
    "label_manifest",
    "rejected_events",
    "seal_receipt",
    "seal_sidecar",
)


class ActiveReleaseError(RuntimeError):
    """Authoritative active-release artifact unavailable or inconsistent."""


def default_live_roots(
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """Resolve default live_root / declared pack / seal dir from constants."""
    root = live_root if live_root is not None else C.OUT_ROOT
    pack = live_pack_path if live_pack_path is not None else C.CANONICAL_PACK_PATH
    seal = live_seal_dir if live_seal_dir is not None else C.SEAL_DIR
    return {"live_root": root, "live_pack_path": pack, "live_seal_dir": seal}


def active_artifacts(
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """Authoritative paths for the active release (CURRENT when present)."""
    roots = default_live_roots(
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    return resolve_live_artifacts(
        live_root=roots["live_root"],
        live_pack_path=roots["live_pack_path"],
        live_seal_dir=roots["live_seal_dir"],
    )


def current_is_set(*, live_root: Optional[Path] = None) -> bool:
    root = live_root if live_root is not None else C.OUT_ROOT
    return resolve_current_release(root) is not None


def require_artifact(
    key: str,
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Path:
    """Return an authoritative artifact path; fail closed if missing."""
    if key not in ACTIVE_READ_KEYS and key not in GOVERNED_CONSUMER_KEYS:
        raise ActiveReleaseError(f"unknown active-release artifact key={key!r}")
    arts = active_artifacts(
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    path = arts[key]
    if not path.exists() or not path.is_file():
        release = arts.get("release_dir")
        cur = current_is_set(live_root=live_root)
        raise ActiveReleaseError(
            f"authoritative artifact unavailable key={key!r} path={path} "
            f"current_set={cur} release_dir={release}"
        )
    return path


def load_json_artifact(
    key: str,
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Any:
    path = require_artifact(
        key,
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    return json.loads(path.read_text(encoding="utf-8"))


def load_canonical_pack(
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load the authoritative canonical schedule pack for the active release.

    Fails closed when the pack is unavailable (no soft present=false).
    """
    raw = load_json_artifact(
        "pack_path",
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    if not isinstance(raw, dict):
        raise ActiveReleaseError("canonical pack must be a JSON object")
    return raw


def load_feature_content(**kwargs: Any) -> Any:
    return load_json_artifact("feature_content", **kwargs)


def load_feature_manifest(**kwargs: Any) -> Any:
    return load_json_artifact("feature_manifest", **kwargs)


def load_label_content(**kwargs: Any) -> Any:
    return load_json_artifact("label_content", **kwargs)


def load_label_manifest(**kwargs: Any) -> Any:
    return load_json_artifact("label_manifest", **kwargs)


def load_rejected_events(**kwargs: Any) -> Any:
    return load_json_artifact("rejected_events", **kwargs)


def load_seal_receipt(**kwargs: Any) -> Any:
    return load_json_artifact("seal_receipt", **kwargs)


def load_evaluator_inputs(
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Future evaluator inputs — paths + sha256s from one active release.

    Does not unseal or score. Fails closed if any governed input is missing.
    """
    arts = active_artifacts(
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    roots = default_live_roots(
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    identity = consumer_release_identity(
        live_root=roots["live_root"],
        live_pack_path=roots["live_pack_path"],
        live_seal_dir=roots["live_seal_dir"],
    )
    required = (
        "feature_content",
        "feature_manifest",
        "label_content",
        "label_manifest",
        "rejected_events",
        "pack_path",
        "seal_receipt",
    )
    paths: Dict[str, str] = {}
    hashes: Dict[str, str] = {}
    for key in required:
        path = require_artifact(
            key,
            live_root=live_root,
            live_pack_path=live_pack_path,
            live_seal_dir=live_seal_dir,
        )
        paths[key] = str(path)
        hashes[key] = sha256_file(path)
    return {
        "holdout_id": C.HOLDOUT_ID,
        "season_key": C.SEASON_KEY,
        "current_set": identity["current_set"],
        "release_dir": identity["release_dir"],
        "paths": paths,
        "sha256": hashes,
        "feature_package": str(arts["feature_package"]),
        "label_package": str(arts["label_package"]),
        "seal_dir": str(arts["seal_dir"]),
        "scoring_authorized": False,
    }


def canonical_pack_path_for_active(
    *,
    live_root: Optional[Path] = None,
    live_pack_path: Optional[Path] = None,
    live_seal_dir: Optional[Path] = None,
) -> Path:
    """Path to the authoritative pack (CURRENT release when set)."""
    return active_artifacts(
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )["pack_path"]


def assert_no_flat_authoritative_bypass(
    *,
    live_root: Optional[Path] = None,
    flat_paths: Optional[Mapping[str, Path]] = None,
) -> None:
    """When CURRENT exists, flat legacy paths must not be treated as SoT.

    Raises if a caller-supplied flat path exists and differs from the active
    release artifact (detects dual-reality reads).
    """
    if not current_is_set(live_root=live_root):
        return
    arts = active_artifacts(live_root=live_root)
    flats = dict(flat_paths or {})
    if not flats:
        flats = {
            "feature_content": C.FEATURE_DIR / "features.json",
            "label_content": C.LABEL_DIR / "labels.json",
            "seal_receipt": C.SEAL_DIR / "seal_receipt.json",
            "pack_path": C.CANONICAL_PACK_PATH,
            "rejected_events": C.REJECTED_DIR / "rejected_events.json",
        }
    for key, flat in flats.items():
        if key not in arts:
            continue
        active = arts[key]
        if not flat.exists() or not flat.is_file():
            continue
        if not active.exists() or not active.is_file():
            raise ActiveReleaseError(
                f"CURRENT set but authoritative {key} missing while flat path "
                f"exists at {flat}"
            )
        if flat.resolve() == active.resolve():
            continue
        if sha256_file(flat) != sha256_file(active):
            raise ActiveReleaseError(
                f"dual-reality: flat {key} at {flat} differs from active "
                f"release artifact at {active}"
            )
