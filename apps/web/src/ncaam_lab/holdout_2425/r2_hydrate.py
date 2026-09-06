"""R2 hydrate for frozen v1.1 packages (Phase 2.6F CR4).

Features hydrate uses features-bucket credentials only.
Label-vault hydrate is a SEPARATE governed path — builders fail closed.
No Odds API / live-data fallback. Credential-free receipts only.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Protocol

from ncaam_lab.holdout_2425.locked_identity import locked_expected_hashes
from ncaam_lab.holdout_2425.r2_storage_contract import (
    FEATURES_BUCKET,
    FEATURES_ENV,
    FEATURES_ROLES,
    LABEL_VAULT_BUCKET,
    LABEL_VAULT_ENV,
    LABEL_VAULT_ROLES,
    ROLE_STAGING_RELPATH,
    ROLE_TO_LOCKED_HASH_KEY,
    cas_object_key,
)


class AccessRole(str, Enum):
    BUILDER = "builder"
    GOVERNED_EVALUATOR = "governed_evaluator"


class HydrateError(RuntimeError):
    """Fail-closed hydrate / vault access error (never embeds object body)."""


class LabelVaultAccessDenied(HydrateError):
    """Builders must never call label-vault hydrate or receive vault credentials."""


class ObjectStore(Protocol):
    def get_object(self, *, bucket: str, key: str) -> bytes: ...

    def object_exists(self, *, bucket: str, key: str) -> bool: ...


@dataclass
class MockR2Store:
    """In-memory R2 stand-in for unit tests (no network, no credentials)."""

    objects: MutableMapping[tuple[str, str], bytes] = field(default_factory=dict)
    restricted_keys: set[tuple[str, str]] = field(default_factory=set)

    def put(self, *, bucket: str, key: str, body: bytes) -> None:
        self.objects[(bucket, key)] = body

    def restrict(self, *, bucket: str, key: str) -> None:
        self.restricted_keys.add((bucket, key))

    def object_exists(self, *, bucket: str, key: str) -> bool:
        return (bucket, key) in self.objects

    def get_object(self, *, bucket: str, key: str) -> bytes:
        loc = (bucket, key)
        if loc in self.restricted_keys:
            raise HydrateError(
                f"restricted object access denied bucket={bucket!r} key={key!r}"
            )
        if loc not in self.objects:
            raise HydrateError(
                f"missing object bucket={bucket!r} key={key!r}"
            )
        return self.objects[loc]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scrub_value(v: Any) -> Any:
    forbidden_substrings = (
        "secret",
        "access_key",
        "password",
        "token",
        "credential",
        "aws_secret",
    )
    if isinstance(v, dict):
        return {
            k: _scrub_value(vv)
            for k, vv in v.items()
            if not any(s in str(k).lower() for s in forbidden_substrings)
        }
    if isinstance(v, list):
        return [_scrub_value(x) for x in v]
    return v


def _scrub_receipt(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    """Ensure recovery/hydrate receipts never carry credential material."""
    out = _scrub_value(dict(receipt))
    assert isinstance(out, dict)
    out["credentials_included"] = False
    return out


def resolve_features_bucket_config(
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    e = dict(env or os.environ)
    bucket = e.get(FEATURES_ENV["bucket"]) or FEATURES_BUCKET
    endpoint = e.get(FEATURES_ENV["endpoint"])
    account = e.get(FEATURES_ENV["account_id"])
    if not endpoint and account:
        endpoint = f"https://{account}.r2.cloudflarestorage.com"
    return {
        "bucket": bucket,
        "endpoint": endpoint,
        "prefix": e.get(FEATURES_ENV["prefix"]) or "",
        "has_access_key": bool(e.get(FEATURES_ENV["access_key_id"])),
        "has_secret": bool(e.get(FEATURES_ENV["secret_access_key"])),
        # Never return secret values.
    }


def resolve_label_vault_config(
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    e = dict(env or os.environ)
    bucket = e.get(LABEL_VAULT_ENV["bucket"]) or LABEL_VAULT_BUCKET
    endpoint = e.get(LABEL_VAULT_ENV["endpoint"])
    account = e.get(LABEL_VAULT_ENV["account_id"])
    if not endpoint and account:
        endpoint = f"https://{account}.r2.cloudflarestorage.com"
    return {
        "bucket": bucket,
        "endpoint": endpoint,
        "prefix": e.get(LABEL_VAULT_ENV["prefix"]) or "",
        "has_access_key": bool(e.get(LABEL_VAULT_ENV["access_key_id"])),
        "has_secret": bool(e.get(LABEL_VAULT_ENV["secret_access_key"])),
    }


def boto3_features_client(env: Optional[Mapping[str, str]] = None):
    """Build features-bucket S3 client. Never reads label-vault credentials."""
    try:
        import boto3
    except ImportError as exc:
        raise HydrateError(
            "boto3 required for real R2 hydrate; no Odds API / live-data fallback"
        ) from exc
    e = dict(env or os.environ)
    cfg = resolve_features_bucket_config(e)
    if not cfg["endpoint"]:
        raise HydrateError(
            f"Set {FEATURES_ENV['endpoint']} or {FEATURES_ENV['account_id']} "
            "(features bucket only)."
        )
    key = e.get(FEATURES_ENV["access_key_id"])
    secret = e.get(FEATURES_ENV["secret_access_key"])
    if not key or not secret:
        raise HydrateError(
            "Missing features-bucket credentials "
            f"({FEATURES_ENV['access_key_id']} + {FEATURES_ENV['secret_access_key']}). "
            "Refusing Odds API / unsigned public fallback."
        )
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=e.get("AWS_REGION", "auto"),
    )


def boto3_label_vault_client(
    *,
    role: AccessRole,
    env: Optional[Mapping[str, str]] = None,
):
    """Build label-vault S3 client. Builders fail closed before any network call."""
    if role != AccessRole.GOVERNED_EVALUATOR:
        raise LabelVaultAccessDenied(
            "builders cannot access label vault "
            f"(role={role.value!r}); governed evaluator after explicit unseal only"
        )
    try:
        import boto3
    except ImportError as exc:
        raise HydrateError(
            "boto3 required for label-vault hydrate; no Odds API fallback"
        ) from exc
    e = dict(env or os.environ)
    cfg = resolve_label_vault_config(e)
    if not cfg["endpoint"]:
        raise HydrateError(
            f"Set {LABEL_VAULT_ENV['endpoint']} or {LABEL_VAULT_ENV['account_id']} "
            "(label vault only)."
        )
    key = e.get(LABEL_VAULT_ENV["access_key_id"])
    secret = e.get(LABEL_VAULT_ENV["secret_access_key"])
    if not key or not secret:
        raise HydrateError(
            "Missing label-vault credentials for governed evaluator. "
            "Builders must never receive these credentials."
        )
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=e.get("AWS_REGION", "auto"),
    )


@dataclass
class Boto3ObjectStore:
    client: Any
    # Optional allowlist of buckets this store may touch.
    allowed_buckets: Optional[set[str]] = None

    def object_exists(self, *, bucket: str, key: str) -> bool:
        if self.allowed_buckets is not None and bucket not in self.allowed_buckets:
            raise HydrateError(f"bucket {bucket!r} not allowed for this store")
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception as exc:  # noqa: BLE001 — fail closed, no body leak
            raise HydrateError(
                f"missing or inaccessible object bucket={bucket!r} key={key!r}"
            ) from exc

    def get_object(self, *, bucket: str, key: str) -> bytes:
        if self.allowed_buckets is not None and bucket not in self.allowed_buckets:
            raise HydrateError(f"bucket {bucket!r} not allowed for this store")
        try:
            resp = self.client.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read()
        except Exception as exc:  # noqa: BLE001
            # Never attach response body / label contents to the error.
            raise HydrateError(
                f"failed to fetch object bucket={bucket!r} key={key!r}"
            ) from exc


def _expected_sha_for_role(role: str, inventory_obj: Mapping[str, Any]) -> Optional[str]:
    locked = locked_expected_hashes()
    hash_key = ROLE_TO_LOCKED_HASH_KEY.get(role)
    if hash_key:
        return locked[hash_key]
    return inventory_obj.get("expected_content_sha256")


def _fetch_and_verify(
    store: ObjectStore,
    *,
    bucket: str,
    key: str,
    role: str,
    expected_sha256: Optional[str],
) -> bytes:
    try:
        body = store.get_object(bucket=bucket, key=key)
    except HydrateError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HydrateError(
            f"failed to fetch object role={role!r} bucket={bucket!r} key={key!r}"
        ) from exc
    actual = sha256_bytes(body)
    if expected_sha256 and actual != expected_sha256:
        # Corrupted / wrong object — fail closed; do not echo body.
        raise HydrateError(
            f"corrupted or mismatched object role={role!r} "
            f"expected_sha256={expected_sha256} actual_sha256={actual}"
        )
    return body


def hydrate_features_objects(
    *,
    store: ObjectStore,
    staging_root: Path,
    inventory_objects: List[Mapping[str, Any]],
    bucket: str = FEATURES_BUCKET,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Hydrate features-bucket roles into staging. Never touches label vault."""
    receipt: Dict[str, Any] = {
        "path": "features_bucket_hydrate",
        "bucket": bucket,
        "dry_run": dry_run,
        "odds_api_calls_made": False,
        "live_data_fallback": False,
        "label_vault_touched": False,
        "hydrated": [],
    }
    feature_objs = [
        o
        for o in inventory_objects
        if o.get("role") in FEATURES_ROLES or o.get("bucket") == bucket
    ]
    # Exclude pure label roles even if mis-tagged.
    feature_objs = [o for o in feature_objs if o.get("role") not in LABEL_VAULT_ROLES]
    if dry_run:
        receipt["status"] = "DRY_RUN"
        receipt["roles"] = [o.get("role") for o in feature_objs]
        return _scrub_receipt(receipt)

    staging_root.mkdir(parents=True, exist_ok=True)
    for obj in feature_objs:
        role = str(obj.get("role") or "")
        if role in LABEL_VAULT_ROLES:
            raise HydrateError(
                f"features hydrate refused label role={role!r} "
                "(label vault is a separate governed path)"
            )
        cas_key = obj.get("cas_key")
        if not cas_key:
            # CoS placeholder not yet filled — fail closed for real recovery.
            raise HydrateError(
                f"missing cas_key for features role={role!r} "
                "(CoS must upload and fill refs; refusing substitute generation)"
            )
        expected = _expected_sha_for_role(role, obj)
        # seal_file_sidecar: expected_sha256 in inventory may be seal file hash
        # (text content) while CAS digests the sidecar file bytes — tests seed both.
        if role == "seal_file_sidecar":
            expected = obj.get("expected_content_sha256") or expected
        body = _fetch_and_verify(
            store,
            bucket=str(obj.get("bucket") or bucket),
            key=str(cas_key),
            role=role,
            expected_sha256=expected if role != "seal_file_sidecar" else None,
        )
        if role == "seal_file_sidecar":
            # Sidecar must equal locked seal_file_sha256 text (first token).
            locked_seal_file = locked_expected_hashes()["seal_file_sha256"]
            text = body.decode("utf-8", errors="replace").strip().split()[0]
            if text != locked_seal_file:
                raise HydrateError(
                    "seal_file_sidecar content does not match locked seal_file_sha256"
                )
            if expected and sha256_bytes(body) != expected:
                raise HydrateError(
                    "corrupted seal_file_sidecar object "
                    f"expected_sha256={expected} actual_sha256={sha256_bytes(body)}"
                )
        rel = ROLE_STAGING_RELPATH.get(role)
        if not rel:
            raise HydrateError(f"unknown staging path for role={role!r}")
        dest = staging_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        receipt["hydrated"].append(
            {
                "role": role,
                "cas_key": cas_key,
                "sha256": sha256_bytes(body),
                "dest": rel,
            }
        )
    receipt["status"] = "HYDRATED"
    return _scrub_receipt(receipt)


def hydrate_label_vault_objects(
    *,
    role: AccessRole,
    store: ObjectStore,
    staging_root: Path,
    inventory_objects: List[Mapping[str, Any]],
    bucket: str = LABEL_VAULT_BUCKET,
    dry_run: bool = False,
    authorize_unseal: bool = False,
) -> Dict[str, Any]:
    """Governed label-vault hydrate. Builders fail closed before any fetch."""
    if role != AccessRole.GOVERNED_EVALUATOR:
        raise LabelVaultAccessDenied(
            "builders cannot access label vault; "
            "label hydrate requires AccessRole.GOVERNED_EVALUATOR"
        )
    if not authorize_unseal:
        raise LabelVaultAccessDenied(
            "label vault hydrate requires explicit unseal authorization "
            "(authorize_unseal=True); refusing"
        )
    receipt: Dict[str, Any] = {
        "path": "label_vault_hydrate",
        "bucket": bucket,
        "dry_run": dry_run,
        "access_role": role.value,
        "authorize_unseal": True,
        "odds_api_calls_made": False,
        "live_data_fallback": False,
        "hydrated": [],
        # Never include label body bytes in receipt.
        "label_contents_included_in_receipt": False,
    }
    label_objs = [
        o
        for o in inventory_objects
        if o.get("role") in LABEL_VAULT_ROLES or o.get("bucket") == bucket
    ]
    label_objs = [o for o in label_objs if o.get("role") in LABEL_VAULT_ROLES]
    if dry_run:
        receipt["status"] = "DRY_RUN"
        receipt["roles"] = [o.get("role") for o in label_objs]
        return _scrub_receipt(receipt)

    staging_root.mkdir(parents=True, exist_ok=True)
    for obj in label_objs:
        obj_role = str(obj.get("role") or "")
        cas_key = obj.get("cas_key")
        if not cas_key:
            raise HydrateError(
                f"missing cas_key for label role={obj_role!r} "
                "(CoS must upload; refusing substitute generation)"
            )
        expected = _expected_sha_for_role(obj_role, obj)
        try:
            body = _fetch_and_verify(
                store,
                bucket=str(obj.get("bucket") or bucket),
                key=str(cas_key),
                role=obj_role,
                expected_sha256=expected,
            )
        except HydrateError as exc:
            # Re-raise without attaching label body (ensure message has no payload).
            msg = str(exc)
            if "label" in msg.lower() and len(msg) > 500:
                raise HydrateError(
                    f"label vault object failed closed role={obj_role!r}"
                ) from None
            raise HydrateError(msg) from None
        rel = ROLE_STAGING_RELPATH[obj_role]
        dest = staging_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        receipt["hydrated"].append(
            {
                "role": obj_role,
                "cas_key": cas_key,
                "sha256": sha256_bytes(body),
                "dest": rel,
                # Explicitly omit content.
            }
        )
    receipt["status"] = "HYDRATED"
    return _scrub_receipt(receipt)


def builder_must_not_access_label_vault(
    *,
    role: AccessRole = AccessRole.BUILDER,
    **kwargs: Any,
) -> None:
    """Test/ops helper: prove builder path cannot open label vault."""
    hydrate_label_vault_objects(role=role, authorize_unseal=True, **kwargs)


def seed_mock_store_from_bytes(
    store: MockR2Store,
    *,
    role_bytes: Mapping[str, bytes],
    features_bucket: str = FEATURES_BUCKET,
    label_bucket: str = LABEL_VAULT_BUCKET,
) -> List[Dict[str, Any]]:
    """Seed a mock store with exact role bytes; return inventory object entries."""
    inventory: List[Dict[str, Any]] = []
    for role, body in role_bytes.items():
        digest = sha256_bytes(body)
        bucket = label_bucket if role in LABEL_VAULT_ROLES else features_bucket
        key = cas_object_key(digest)
        store.put(bucket=bucket, key=key, body=body)
        entry: Dict[str, Any] = {
            "role": role,
            "bucket": bucket,
            "expected_content_sha256": digest,
            "cas_key": key,
            "logical_path": ROLE_STAGING_RELPATH.get(role),
            "upload_status": "MOCK_SEEDED",
            "retention": "indefinite",
        }
        inventory.append(entry)
    return inventory
