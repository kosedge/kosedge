#!/usr/bin/env python3
"""R2 hydrate helpers for Phase 2.6F CR4 frozen holdout packages.

Features-bucket hydrate uses features credentials only.
Label-vault hydrate is a SEPARATE governed path (builders fail closed).

Prefer the full Path B recovery entrypoint:
  python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py \\
      --governed-evaluator --authorize-unseal

This script supports role-scoped hydrate for ops / dry-run checks.
No Odds API. No invented endpoints. Credential-free receipts.

Env placeholders (CoS fills after provisioning — never commit secrets):
  NCAAM_HOLDOUT_FEATURES_R2_* / NCAAM_HOLDOUT_LABEL_VAULT_R2_*
  See apps/web/src/ncaam_lab/holdout_2425/r2_storage_contract.py

Legacy ESPN raw hydrate (gap-recovery bucket) remains available as
--role espn_schedule_raw_v1 for forensic input hydration only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from ncaam_lab.holdout_2425.r2_hydrate import (  # noqa: E402
    AccessRole,
    HydrateError,
    LabelVaultAccessDenied,
    boto3_features_client,
    boto3_label_vault_client,
)
from ncaam_lab.holdout_2425.r2_storage_contract import (  # noqa: E402
    default_package_inventory,
    storage_contract_summary,
)

REFS_PATH = (
    REPO
    / "data"
    / "ops"
    / "lab"
    / "ncaam"
    / "holdout_2024_25"
    / "r2_object_refs"
    / "r2_object_refs_v1.json"
)
OUT_RAW = (
    REPO
    / "data"
    / "ops"
    / "lab"
    / "ncaam"
    / "holdout_2024_25"
    / "raw"
    / "espn_scoreboard"
)


def _load_refs() -> Dict[str, Any]:
    if not REFS_PATH.exists():
        raise SystemExit(
            f"Missing locked R2 refs at {REFS_PATH.relative_to(REPO)}. "
            "PR B governance artifacts required for legacy raw hydrate; "
            "CR4 package inventory falls back to storage_contract defaults."
        )
    return json.loads(REFS_PATH.read_text(encoding="utf-8"))


def _role(refs: Dict[str, Any], role: str) -> Dict[str, Any]:
    for obj in refs.get("objects") or []:
        if obj.get("role") == role:
            return obj
    raise SystemExit(f"Role {role!r} not found in {REFS_PATH}")


def hydrate_espn_raw(*, dry_run: bool = False) -> Dict[str, Any]:
    """FORENSIC input helper — ESPN raw from legacy gap-recovery bucket.

    Does not define or promote the frozen holdout package.
    """
    refs = _load_refs()
    obj = _role(refs, "espn_schedule_raw_v1")
    bucket = refs.get("bucket") or refs.get("legacy_gap_recovery_bucket")
    if not bucket:
        # CR4 refs may nest legacy under a key.
        legacy = refs.get("legacy_gap_recovery_raw") or {}
        bucket = legacy.get("bucket")
        objects = legacy.get("objects") or refs.get("objects") or []
        obj = next((o for o in objects if o.get("role") == "espn_schedule_raw_v1"), obj)
    prefix = obj["prefix"]
    expected_n = int(obj.get("n_objects") or 0)
    receipt: Dict[str, Any] = {
        "path_class": "FORENSIC_ESPN_RAW_HYDRATE",
        "not_frozen_holdout_authority": True,
        "bucket": bucket,
        "prefix": prefix,
        "cas_index_sha256": obj.get("cas_index_sha256"),
        "expected_n_objects": expected_n,
        "dry_run": dry_run,
        "api_calls_made": False,
        "odds_api_calls_made": False,
        "credentials_included": False,
    }
    if dry_run:
        receipt["status"] = "DRY_RUN_REFS_LOCKED"
        return receipt

    # Prefer features-style env if set; else legacy AWS_* for forensic Mac ops.
    try:
        client = boto3_features_client()
    except HydrateError:
        try:
            import boto3
        except ImportError as e:
            raise SystemExit(
                "boto3 required for R2 hydrate. No Odds API fallback."
            ) from e
        account = os.environ.get("R2_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID")
        endpoint = os.environ.get("AWS_ENDPOINT_URL")
        if not endpoint:
            if not account:
                raise SystemExit(
                    "Set R2_ACCOUNT_ID (or AWS_ENDPOINT_URL) for Cloudflare R2 S3 API."
                )
            endpoint = f"https://{account}.r2.cloudflarestorage.com"
        key = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get(
            "R2_SECRET_ACCESS_KEY"
        )
        if not key or not secret:
            raise SystemExit(
                "Missing R2/S3 credentials. Refusing Odds API / unsigned public fetches."
            )
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=os.environ.get("AWS_REGION", "auto"),
        )

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    token = None
    keys: List[str] = []
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for item in resp.get("Contents") or []:
            keys.append(item["Key"])
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")

    if expected_n and len(keys) != expected_n:
        raise SystemExit(
            f"R2 object count mismatch for {prefix}: got {len(keys)}, expected {expected_n}"
        )

    downloaded = 0
    for key in keys:
        name = Path(key).name
        dest = OUT_RAW / name
        client.download_file(bucket, key, str(dest))
        downloaded += 1

    receipt.update(
        {
            "status": "HYDRATED_FORENSIC_RAW",
            "n_downloaded": downloaded,
            "dest": str(OUT_RAW.relative_to(REPO)),
        }
    )
    return receipt


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--role",
        default="features_package_v1",
        choices=[
            "features_package_v1",
            "label_vault_v1",
            "espn_schedule_raw_v1",
            "print_contract",
        ],
        help="Locked R2 role to hydrate.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--governed-evaluator",
        action="store_true",
        help="Required for --role label_vault_v1.",
    )
    parser.add_argument(
        "--authorize-unseal",
        action="store_true",
        help="Required for --role label_vault_v1.",
    )
    parser.add_argument(
        "--builder",
        action="store_true",
        help="Builder role (label vault must fail closed).",
    )
    args = parser.parse_args(argv)

    if args.role == "print_contract":
        print(json.dumps(storage_contract_summary(), indent=2, sort_keys=True))
        return 0

    if args.role == "espn_schedule_raw_v1":
        receipt = hydrate_espn_raw(dry_run=args.dry_run)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    inventory = list(default_package_inventory()["objects"])
    if REFS_PATH.exists():
        refs = json.loads(REFS_PATH.read_text(encoding="utf-8"))
        if isinstance(refs.get("package_inventory"), dict):
            inventory = list(refs["package_inventory"].get("objects") or inventory)

    if args.role == "features_package_v1":
        if args.dry_run:
            receipt = {
                "status": "DRY_RUN",
                "role": args.role,
                "path": "features_bucket_hydrate",
                "odds_api_calls_made": False,
                "label_vault_touched": False,
                "credentials_included": False,
                "storage_contract": storage_contract_summary(),
                "inventory_roles": [
                    o.get("role")
                    for o in inventory
                    if o.get("role") not in ("label_content", "label_manifest")
                ],
            }
            print(json.dumps(receipt, indent=2, sort_keys=True))
            return 0
        # Real features hydrate is performed via recover entrypoint into staging.
        print(
            json.dumps(
                {
                    "status": "USE_RECOVER_ENTRYPOINT",
                    "message": (
                        "Features hydrate into staging is performed by "
                        "recover_2425_sealed_holdout_from_r2.py "
                        "(staging→verify→reseal→promote)."
                    ),
                    "script": "scripts/ncaam/recover_2425_sealed_holdout_from_r2.py",
                    "credentials_included": False,
                },
                indent=2,
            )
        )
        return 0

    if args.role == "label_vault_v1":
        role = (
            AccessRole.GOVERNED_EVALUATOR
            if args.governed_evaluator and not args.builder
            else AccessRole.BUILDER
        )
        if args.dry_run:
            try:
                if role != AccessRole.GOVERNED_EVALUATOR or not args.authorize_unseal:
                    raise LabelVaultAccessDenied(
                        "builders cannot access label vault; "
                        "require --governed-evaluator --authorize-unseal"
                    )
                receipt = {
                    "status": "DRY_RUN",
                    "role": args.role,
                    "access_role": role.value,
                    "authorize_unseal": True,
                    "label_contents_included_in_receipt": False,
                    "credentials_included": False,
                }
                print(json.dumps(receipt, indent=2, sort_keys=True))
                return 0
            except LabelVaultAccessDenied as exc:
                print(
                    json.dumps(
                        {
                            "status": "REFUSED_LABEL_VAULT_ACCESS",
                            "error": str(exc),
                            "label_contents_included_in_receipt": False,
                            "credentials_included": False,
                        },
                        indent=2,
                    )
                )
                return 2
        # Prove boto3 label client construction fails for builders.
        try:
            boto3_label_vault_client(role=role)
        except LabelVaultAccessDenied as exc:
            print(
                json.dumps(
                    {
                        "status": "REFUSED_LABEL_VAULT_ACCESS",
                        "error": str(exc),
                        "label_contents_included_in_receipt": False,
                        "credentials_included": False,
                    },
                    indent=2,
                )
            )
            return 2
        except HydrateError as exc:
            print(
                json.dumps(
                    {
                        "status": "REFUSED_OR_MISSING_ENV",
                        "error": str(exc),
                        "credentials_included": False,
                    },
                    indent=2,
                )
            )
            return 2
        print(
            json.dumps(
                {
                    "status": "USE_RECOVER_ENTRYPOINT",
                    "message": (
                        "Label vault hydrate into staging is performed by "
                        "recover_2425_sealed_holdout_from_r2.py under governed auth."
                    ),
                    "credentials_included": False,
                    "label_contents_included_in_receipt": False,
                },
                indent=2,
            )
        )
        return 0

    raise SystemExit(f"Unsupported role {args.role}")


if __name__ == "__main__":
    raise SystemExit(main())
