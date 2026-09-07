#!/usr/bin/env python3
"""Path B authoritative disaster recovery — hydrate frozen v1.1 packages from private R2.

Phase 2.6F CR4/CR6 (Ryan LOCKED):
  R2 hydrate → staging → verify inventory + locked hashes
  → reseal (frozen v1.1 identity) → release-pointer promote only after pass.

Live seal is never unlinked first. Failures **before** CURRENT switches preserve
the previous package. After the pointer switch there are no required writes
(CR6); never report live_package_preserved=true when CURRENT already moved.
Inventory SoT is Python default_package_inventory() — proves 10/10 UPLOADED with
non-null CAS keys; it does **not** expose per-object provider_verified (that
belongs on the sanitized provider retention receipt). Credential-free receipt.
No Odds API / live-data fallback.

CoS provisions buckets/upload separately. This script reads env-driven endpoint /
bucket / prefix placeholders and locked refs — it does NOT invent credentials.

Builders must not call label-vault hydrate. Full recovery requires
--governed-evaluator --authorize-unseal.

Usage:
  python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py --dry-run
  python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py \\
      --governed-evaluator --authorize-unseal

Real hydrate (after CoS upload) uses features + label-vault env vars documented in
apps/web/src/ncaam_lab/holdout_2425/r2_storage_contract.py.
Unit tests use MockR2Store — this script is the documented real entrypoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from ncaam_lab.holdout_2425 import constants as C  # noqa: E402
from ncaam_lab.holdout_2425.path_b_promote import PromoteError, PromoteVerificationError  # noqa: E402
from ncaam_lab.holdout_2425.path_b_r2_recovery import (  # noqa: E402
    RecoveryError,
    recover_from_r2,
)
from ncaam_lab.holdout_2425.r2_hydrate import (  # noqa: E402
    AccessRole,
    Boto3ObjectStore,
    HydrateError,
    LabelVaultAccessDenied,
    boto3_features_client,
    boto3_label_vault_client,
)
from ncaam_lab.holdout_2425.r2_storage_contract import (  # noqa: E402
    FEATURES_BUCKET,
    LABEL_VAULT_BUCKET,
    default_package_inventory,
    storage_contract_summary,
)

REFS_PATH = C.OUT_ROOT / "r2_object_refs" / "r2_object_refs_v1.json"


def _canonical_object_fingerprint(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Stable subset used to compare Python SoT vs checked-in refs inventory."""
    keys = (
        "role",
        "bucket",
        "expected_content_sha256",
        "cas_key",
        "fixed_key",
        "sidecar_file_sha256",
        "sidecar_text_sha256_of_seal_file",
        "logical_path",
        "upload_status",
        "retention",
    )
    return {k: obj.get(k) for k in keys if k in obj or k in ("cas_key", "fixed_key")}


def _load_inventory() -> List[Dict[str, Any]]:
    """Canonical inventory = Python default_package_inventory() (CoS-verified).

    Checked-in r2_object_refs JSON must match when present. Never prefer stale
    PENDING_COS / null-CAS placeholders over the verified Python contract.
    """
    canonical = list(default_package_inventory()["objects"])
    if not REFS_PATH.exists():
        return canonical

    refs = json.loads(REFS_PATH.read_text(encoding="utf-8"))
    checked_in: List[Dict[str, Any]] | None = None
    if "package_inventory" in refs:
        inv = refs["package_inventory"]
        if isinstance(inv, dict) and "objects" in inv:
            checked_in = list(inv["objects"])
    if checked_in is None and "cr4_package_inventory_objects" in refs:
        checked_in = list(refs["cr4_package_inventory_objects"])

    if checked_in is None:
        return canonical

    # Lockstep gate: checked-in objects must equal Python SoT fingerprints.
    can_by_role = {o["role"]: _canonical_object_fingerprint(o) for o in canonical}
    ref_by_role = {o["role"]: _canonical_object_fingerprint(o) for o in checked_in}
    if set(can_by_role) != set(ref_by_role):
        raise SystemExit(
            json.dumps(
                {
                    "status": "REFUSED_INVENTORY_DRIFT",
                    "error": "checked-in r2_object_refs roles != Python default_package_inventory",
                    "python_roles": sorted(can_by_role),
                    "refs_roles": sorted(ref_by_role),
                    "credentials_included": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    drift = []
    for role in sorted(can_by_role):
        if can_by_role[role] != ref_by_role[role]:
            drift.append(
                {
                    "role": role,
                    "python": can_by_role[role],
                    "refs_json": ref_by_role[role],
                }
            )
    if drift:
        raise SystemExit(
            json.dumps(
                {
                    "status": "REFUSED_INVENTORY_DRIFT",
                    "error": "checked-in package_inventory does not match verified Python SoT",
                    "drift": drift,
                    "credentials_included": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    # Prefer Python objects (single source); refs JSON verified equal.
    return canonical

def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print storage contract + recovery plan; no download/promote.",
    )
    parser.add_argument(
        "--governed-evaluator",
        action="store_true",
        help="Run as governed evaluator (required for label-vault hydrate).",
    )
    parser.add_argument(
        "--authorize-unseal",
        action="store_true",
        help="Explicit unseal authorization for label-vault access (required).",
    )
    parser.add_argument(
        "--builder",
        action="store_true",
        help="Builder role (must fail closed on label vault).",
    )
    parser.add_argument(
        "--print-contract",
        action="store_true",
        help="Print storage contract summary and exit.",
    )
    args = parser.parse_args(argv)

    if args.print_contract:
        print(json.dumps(storage_contract_summary(), indent=2, sort_keys=True))
        return 0

    if args.builder and args.governed_evaluator:
        print(
            json.dumps(
                {
                    "status": "REFUSED",
                    "error": "specify either --builder or --governed-evaluator, not both",
                    "credentials_included": False,
                },
                indent=2,
            )
        )
        return 2

    role = (
        AccessRole.BUILDER
        if args.builder or not args.governed_evaluator
        else AccessRole.GOVERNED_EVALUATOR
    )
    inventory = _load_inventory()

    if args.dry_run:
        receipt = recover_from_r2(
            features_store=None,  # type: ignore[arg-type]
            label_store=None,  # type: ignore[arg-type]
            inventory_objects=inventory,
            live_root=C.OUT_ROOT,
            live_pack_path=C.CANONICAL_PACK_PATH,
            live_seal_dir=C.SEAL_DIR,
            access_role=role,
            authorize_unseal=args.authorize_unseal,
            dry_run=True,
        )
        receipt["storage_contract"] = storage_contract_summary()
        receipt["inventory_n_objects"] = len(inventory)
        receipt["refs_path"] = (
            str(REFS_PATH.relative_to(REPO)) if REFS_PATH.exists() else None
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    try:
        feat_client = boto3_features_client()
        features_store = Boto3ObjectStore(
            feat_client, allowed_buckets={FEATURES_BUCKET}
        )
        label_client = boto3_label_vault_client(role=role)
        label_store = Boto3ObjectStore(
            label_client, allowed_buckets={LABEL_VAULT_BUCKET}
        )
        receipt = recover_from_r2(
            features_store=features_store,
            label_store=label_store,
            inventory_objects=inventory,
            live_root=C.OUT_ROOT,
            live_pack_path=C.CANONICAL_PACK_PATH,
            live_seal_dir=C.SEAL_DIR,
            access_role=role,
            authorize_unseal=args.authorize_unseal,
            dry_run=False,
        )
    except (
        LabelVaultAccessDenied,
        HydrateError,
        RecoveryError,
        PromoteVerificationError,
        PromoteError,
        OSError,
    ) as exc:
        receipt = getattr(exc, "receipt", None)
        if not isinstance(receipt, dict):
            # Fallback only when the exception carried no receipt. Do not claim
            # preservation without knowing whether CURRENT moved.
            receipt = {
                "status": "REFUSED_OR_FAILED",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "live_package_preserved": None,
                "credentials_included": False,
            }
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
