"""Path B authoritative disaster recovery via private R2 (Phase 2.6F CR4).

Flow (locked):
  R2 hydrate → staging → verify inventory + all locked hashes
  → reseal from downloaded packages with frozen v1.1 identity
  → atomic promote only after pass

Live seal is never unlinked first. Any failure preserves the previous package.
Credential-free recovery receipt. No Odds API / live-data fallback.
Raw+KenPom+odds reconstruction is a SEPARATE forensic path and must not call
this promote path to redefine the frozen holdout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from ncaam_lab.holdout_2425.locked_identity import locked_expected_hashes
from ncaam_lab.holdout_2425.path_b_promote import (
    PromoteVerificationError,
    cleanup_staging,
    collect_staging_hashes,
    promote_staging_to_live,
    sha256_file,
    verify_against_locked,
)
from ncaam_lab.holdout_2425.r2_hydrate import (
    AccessRole,
    HydrateError,
    LabelVaultAccessDenied,
    ObjectStore,
    hydrate_features_objects,
    hydrate_label_vault_objects,
    sha256_bytes,
)
from ncaam_lab.holdout_2425.r2_storage_contract import (
    FEATURES_BUCKET,
    LABEL_VAULT_BUCKET,
    ROLE_STAGING_RELPATH,
)
from ncaam_lab.holdout_2425.seal_package import reseal_from_content_packages


class RecoveryError(RuntimeError):
    """Path B R2 recovery failed closed; live package preserved."""


def _scrub_value(v: Any) -> Any:
    forbidden = ("secret", "access_key", "password", "token", "credential")
    if isinstance(v, dict):
        return {
            k: _scrub_value(vv)
            for k, vv in v.items()
            if not any(s in str(k).lower() for s in forbidden)
        }
    if isinstance(v, list):
        return [_scrub_value(x) for x in v]
    return v


def _scrub(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop credential-like keys; stamp credentials_included only at top level."""
    out = _scrub_value(dict(receipt))
    assert isinstance(out, dict)
    out["credentials_included"] = False
    return out


def _snapshot_live_package(
    *,
    live_root: Path,
    live_pack_path: Path,
    live_seal_dir: Path,
) -> Dict[str, Optional[bytes]]:
    snap: Dict[str, Optional[bytes]] = {}
    seal = live_seal_dir / "seal_receipt.json"
    side = live_seal_dir / "seal_receipt.file_sha256"
    snap["seal"] = seal.read_bytes() if seal.exists() else None
    snap["seal_sidecar"] = side.read_bytes() if side.exists() else None
    snap["pack"] = live_pack_path.read_bytes() if live_pack_path.exists() else None
    feat = live_root / "feature_package" / "features.json"
    lab = live_root / "label_package" / "labels.json"
    snap["features"] = feat.read_bytes() if feat.exists() else None
    snap["labels"] = lab.read_bytes() if lab.exists() else None
    return snap


def _assert_live_unchanged(
    snap: Mapping[str, Optional[bytes]],
    *,
    live_root: Path,
    live_pack_path: Path,
    live_seal_dir: Path,
) -> None:
    seal = live_seal_dir / "seal_receipt.json"
    side = live_seal_dir / "seal_receipt.file_sha256"
    if snap["seal"] is not None:
        if not seal.exists() or seal.read_bytes() != snap["seal"]:
            raise RecoveryError(
                "FAIL-CLOSED: live seal mutated before successful promote"
            )
    if snap["seal_sidecar"] is not None:
        if not side.exists() or side.read_bytes() != snap["seal_sidecar"]:
            raise RecoveryError(
                "FAIL-CLOSED: live seal sidecar mutated before successful promote"
            )
    if snap["pack"] is not None:
        if not live_pack_path.exists() or live_pack_path.read_bytes() != snap["pack"]:
            raise RecoveryError(
                "FAIL-CLOSED: live canonical pack mutated before successful promote"
            )


def verify_inventory_and_locked_hashes(
    *,
    staging_root: Path,
    staging_pack_path: Path,
    inventory_objects: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Verify every inventoried locked role matches on-disk staging + locked hashes."""
    locked = locked_expected_hashes()
    checked: List[str] = []
    for obj in inventory_objects:
        role = str(obj.get("role") or "")
        rel = ROLE_STAGING_RELPATH.get(role)
        if not rel:
            continue
        path = staging_root / rel if role != "canonical_pack" else staging_pack_path
        if role == "canonical_pack":
            path = staging_pack_path
        if not path.exists():
            raise PromoteVerificationError(
                f"inventory verify missing staged object role={role!r}"
            )
        actual = sha256_file(path) if role != "seal_file_sidecar" else sha256_bytes(
            path.read_bytes()
        )
        expected = obj.get("expected_content_sha256")
        if role == "seal_file_sidecar":
            text = path.read_text(encoding="utf-8").strip().split()[0]
            if text != locked["seal_file_sha256"]:
                raise PromoteVerificationError(
                    "seal_file_sidecar text does not match locked seal_file_sha256"
                )
            if expected and actual != expected:
                raise PromoteVerificationError(
                    f"inventory hash mismatch role={role!r}"
                )
        elif expected and actual != expected:
            raise PromoteVerificationError(
                f"inventory hash mismatch role={role!r} "
                f"expected={expected} actual={actual}"
            )
        checked.append(role)

    # Full locked hash set via staging collectors (after reseal for manifests/seal).
    return {"inventory_roles_checked": checked, "locked_expected_hashes": locked}


def recover_from_r2(
    *,
    features_store: ObjectStore,
    label_store: ObjectStore,
    inventory_objects: List[Mapping[str, Any]],
    live_root: Path,
    live_pack_path: Path,
    live_seal_dir: Path,
    staging_root: Optional[Path] = None,
    access_role: AccessRole = AccessRole.GOVERNED_EVALUATOR,
    authorize_unseal: bool = False,
    dry_run: bool = False,
    interrupt_after_hydrate: bool = False,
    fail_promote: bool = False,
    require_locked_hashes: bool = True,
) -> Dict[str, Any]:
    """Authoritative Path B recovery.

    Builders (or missing unseal auth) fail closed at label hydrate — live untouched.
    """
    snap = _snapshot_live_package(
        live_root=live_root,
        live_pack_path=live_pack_path,
        live_seal_dir=live_seal_dir,
    )
    receipt: Dict[str, Any] = {
        "recovery_path": "B_authoritative_r2_hydrate_frozen_v1_1",
        "authority": "private_r2_exact_frozen_bytes",
        "forensic_raw_kenpom_odds_path": False,
        "odds_api_calls_made": False,
        "live_data_fallback": False,
        "manual_placement_required": False,
        "dry_run": dry_run,
        "access_role": access_role.value,
        "authorize_unseal": bool(authorize_unseal),
        "live_seal_preserved_until_verify": True,
        "live_seal_existed_before": snap["seal"] is not None,
        "never_unlink_live_seal_first": True,
        "features_bucket": FEATURES_BUCKET,
        "label_vault_bucket": LABEL_VAULT_BUCKET,
        "locked_expected_hashes": locked_expected_hashes(),
        "require_locked_hashes": require_locked_hashes,
    }
    if dry_run:
        receipt["status"] = "DRY_RUN"
        return _scrub(receipt)

    # Builder / unauthorized must fail before mutating staging meaningfully for labels.
    if access_role != AccessRole.GOVERNED_EVALUATOR or not authorize_unseal:
        try:
            hydrate_label_vault_objects(
                role=access_role,
                store=label_store,
                staging_root=staging_root or (live_root / "_path_b_r2_staging"),
                inventory_objects=inventory_objects,
                authorize_unseal=authorize_unseal,
            )
        except LabelVaultAccessDenied as exc:
            receipt.update(
                {
                    "status": "REFUSED_LABEL_VAULT_ACCESS",
                    "error": str(exc),
                    "live_package_preserved": True,
                }
            )
            raise LabelVaultAccessDenied(str(exc)) from exc

    staging = staging_root or (live_root / "_path_b_r2_staging")
    staging_pack = staging / ROLE_STAGING_RELPATH["canonical_pack"]
    if staging.exists():
        cleanup_staging(staging, None)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        feat_receipt = hydrate_features_objects(
            store=features_store,
            staging_root=staging,
            inventory_objects=inventory_objects,
        )
        receipt["features_hydrate"] = feat_receipt

        label_receipt = hydrate_label_vault_objects(
            role=access_role,
            store=label_store,
            staging_root=staging,
            inventory_objects=inventory_objects,
            authorize_unseal=authorize_unseal,
        )
        receipt["label_hydrate"] = label_receipt

        # Live must still be untouched after hydrate.
        _assert_live_unchanged(
            snap,
            live_root=live_root,
            live_pack_path=live_pack_path,
            live_seal_dir=live_seal_dir,
        )

        if interrupt_after_hydrate:
            receipt.update(
                {
                    "status": "INTERRUPTED_AFTER_HYDRATE",
                    "live_package_preserved": True,
                }
            )
            _assert_live_unchanged(
                snap,
                live_root=live_root,
                live_pack_path=live_pack_path,
                live_seal_dir=live_seal_dir,
            )
            return _scrub(receipt)

        # Ensure pack is at staging_pack path for collectors.
        if not staging_pack.exists():
            raise RecoveryError("canonical pack missing after features hydrate")

        inv = verify_inventory_and_locked_hashes(
            staging_root=staging,
            staging_pack_path=staging_pack,
            inventory_objects=inventory_objects,
        )
        receipt["inventory_verify"] = inv

        # Content hashes must already match locked expectations (exact frozen bytes).
        content_actual = {
            "feature_content_sha256": sha256_file(
                staging / ROLE_STAGING_RELPATH["feature_content"]
            ),
            "label_content_sha256": sha256_file(
                staging / ROLE_STAGING_RELPATH["label_content"]
            ),
            "rejected_sha256": sha256_file(
                staging / ROLE_STAGING_RELPATH["rejected"]
            ),
            "canonical_pack_sha256": sha256_file(staging_pack),
        }
        receipt["downloaded_content_hashes"] = content_actual
        for key, want in locked_expected_hashes().items():
            if key in content_actual and content_actual[key] != want:
                raise PromoteVerificationError(
                    f"downloaded content hash mismatch {key}: "
                    f"expected={want} actual={content_actual[key]}"
                )

        # Reseal from downloaded packages with frozen v1.1 identity (real path).
        # Removes any pre-seeded seal under staging so it cannot be silently reused.
        seal_dir = staging / "seal"
        if seal_dir.exists():
            for p in seal_dir.glob("*"):
                if p.is_file():
                    p.unlink()
        seal = reseal_from_content_packages(out_root=staging)
        receipt["reseal"] = {
            "seal_payload_sha256": seal.get("seal_payload_sha256"),
            "seal_file_sha256": seal.get("seal_file_sha256"),
            "feature_manifest_sha256": seal.get("feature_manifest_sha256"),
            "label_manifest_sha256": seal.get("label_manifest_sha256"),
            "preseeded_seal_silently_reused": False,
        }

        actual_hashes = collect_staging_hashes(
            staging_root=staging, staging_pack_path=staging_pack
        )
        receipt["staging_hashes"] = actual_hashes
        if require_locked_hashes:
            verify_against_locked(actual_hashes)
            receipt["locked_hash_verification"] = "PASS"
        else:
            receipt["locked_hash_verification"] = "SKIPPED"

        _assert_live_unchanged(
            snap,
            live_root=live_root,
            live_pack_path=live_pack_path,
            live_seal_dir=live_seal_dir,
        )

        if fail_promote:
            raise RecoveryError("injected promote failure (test harness)")

        promote_receipt = promote_staging_to_live(
            staging_root=staging,
            staging_pack_path=staging_pack,
            live_root=live_root,
            live_pack_path=live_pack_path,
            live_seal_dir=live_seal_dir,
        )
        receipt["promote"] = promote_receipt
        receipt["status"] = "RECOVERED_VERIFIED_PROMOTED"
        return _scrub(receipt)

    except (PromoteVerificationError, HydrateError, LabelVaultAccessDenied, RecoveryError) as exc:
        # Preserve previous live package bytes on any failure.
        _assert_live_unchanged(
            snap,
            live_root=live_root,
            live_pack_path=live_pack_path,
            live_seal_dir=live_seal_dir,
        )
        # If somehow seal was touched, restore snapshot.
        if snap["seal"] is not None:
            live_seal_dir.mkdir(parents=True, exist_ok=True)
            seal_path = live_seal_dir / "seal_receipt.json"
            if not seal_path.exists() or seal_path.read_bytes() != snap["seal"]:
                seal_path.write_bytes(snap["seal"])
            if snap["seal_sidecar"] is not None:
                (live_seal_dir / "seal_receipt.file_sha256").write_bytes(
                    snap["seal_sidecar"]
                )
        if snap["pack"] is not None:
            if not live_pack_path.exists() or live_pack_path.read_bytes() != snap["pack"]:
                live_pack_path.parent.mkdir(parents=True, exist_ok=True)
                live_pack_path.write_bytes(snap["pack"])
        receipt.update(
            {
                "status": "REFUSED_OR_FAILED_LIVE_PRESERVED",
                "error": str(exc),
                "live_package_preserved": True,
                "error_type": type(exc).__name__,
            }
        )
        # Attach receipt for callers without leaking secrets.
        exc.receipt = _scrub(receipt)  # type: ignore[attr-defined]
        raise
    finally:
        cleanup_staging(staging, None)
