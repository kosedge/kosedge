#!/usr/bin/env python3
"""Deterministic locked-R2 hydration for the 2024–25 sealed holdout package.

Uses EXACT object references from:
  data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/r2_object_refs_v1.json

No Odds API calls. No invented endpoints. Fails closed if refs/env missing.

Env (required for download):
  R2_ACCOUNT_ID / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
  (or AWS_ENDPOINT_URL pointing at the Cloudflare R2 S3 API)

Usage:
  python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --dry-run
  python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --role espn_schedule_raw_v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
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
            "PR B governance artifacts required before hydrate."
        )
    return json.loads(REFS_PATH.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _role(refs: Dict[str, Any], role: str) -> Dict[str, Any]:
    for obj in refs.get("objects") or []:
        if obj.get("role") == role:
            return obj
    raise SystemExit(f"Role {role!r} not found in {REFS_PATH}")


def _boto3_client():
    try:
        import boto3
    except ImportError as e:
        raise SystemExit(
            "boto3 required for R2 hydrate. Install in the worker venv; "
            "no alternate Odds API path exists."
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
            "Missing R2/S3 credentials (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY). "
            "Refusing to invent Odds API calls or unsigned public fetches."
        )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=os.environ.get("AWS_REGION", "auto"),
    )


def hydrate_espn_raw(*, dry_run: bool = False) -> Dict[str, Any]:
    refs = _load_refs()
    obj = _role(refs, "espn_schedule_raw_v1")
    bucket = refs["bucket"]
    prefix = obj["prefix"]
    expected_n = int(obj.get("n_objects") or 0)
    receipt = {
        "bucket": bucket,
        "prefix": prefix,
        "cas_index_sha256": obj.get("cas_index_sha256"),
        "expected_n_objects": expected_n,
        "dry_run": dry_run,
        "api_calls_made": False,
        "odds_api_calls_made": False,
    }
    if dry_run:
        receipt["status"] = "DRY_RUN_REFS_LOCKED"
        return receipt

    client = _boto3_client()
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
            "status": "HYDRATED",
            "n_downloaded": downloaded,
            "dest": str(OUT_RAW.relative_to(REPO)),
        }
    )
    return receipt


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--role",
        default="espn_schedule_raw_v1",
        choices=["espn_schedule_raw_v1"],
        help="Locked R2 role to hydrate (exact refs only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate refs only; do not download.",
    )
    args = parser.parse_args(argv)
    if args.role == "espn_schedule_raw_v1":
        receipt = hydrate_espn_raw(dry_run=args.dry_run)
    else:
        raise SystemExit(f"Unsupported role {args.role}")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
