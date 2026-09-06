"""Private R2 storage contract for frozen v1.1 holdout disaster recovery (Phase 2.6F CR4).

CoS provisions real buckets/upload separately. This module documents the contract
and env-driven placeholders only — no credentials, secrets, or invented uploads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from ncaam_lab.holdout_2425.locked_identity import locked_expected_hashes

# Separate private buckets (public access + r2.dev disabled; no custom domains).
FEATURES_BUCKET = "kosedge-ncaam-holdout-2425-features-v1"
LABEL_VAULT_BUCKET = "kosedge-ncaam-holdout-2425-label-vault-v1"

# Env placeholders CoS fills after provisioning (never commit secrets).
FEATURES_ENV = {
    "endpoint": "NCAAM_HOLDOUT_FEATURES_R2_ENDPOINT",
    "account_id": "NCAAM_HOLDOUT_FEATURES_R2_ACCOUNT_ID",
    "access_key_id": "NCAAM_HOLDOUT_FEATURES_R2_ACCESS_KEY_ID",
    "secret_access_key": "NCAAM_HOLDOUT_FEATURES_R2_SECRET_ACCESS_KEY",
    "bucket": "NCAAM_HOLDOUT_FEATURES_R2_BUCKET",
    "prefix": "NCAAM_HOLDOUT_FEATURES_R2_PREFIX",
}
LABEL_VAULT_ENV = {
    "endpoint": "NCAAM_HOLDOUT_LABEL_VAULT_R2_ENDPOINT",
    "account_id": "NCAAM_HOLDOUT_LABEL_VAULT_R2_ACCOUNT_ID",
    "access_key_id": "NCAAM_HOLDOUT_LABEL_VAULT_R2_ACCESS_KEY_ID",
    "secret_access_key": "NCAAM_HOLDOUT_LABEL_VAULT_R2_SECRET_ACCESS_KEY",
    "bucket": "NCAAM_HOLDOUT_LABEL_VAULT_R2_BUCKET",
    "prefix": "NCAAM_HOLDOUT_LABEL_VAULT_R2_PREFIX",
}

# Frozen v1.1 CAS prefix (indefinite retention lock — CoS applies provider rule).
FROZEN_V1_1_CAS_PREFIX = "ncaam/holdout_2024_25/v1_1/cas/"
FROZEN_V1_1_MANIFEST_PREFIX = "ncaam/holdout_2024_25/v1_1/manifests/"
FROZEN_V1_1_INVENTORY_KEY = "ncaam/holdout_2024_25/v1_1/package_inventory.json"
FROZEN_V1_1_PROVENANCE_KEY = "ncaam/holdout_2024_25/v1_1/provenance_receipt.json"

# Logical roles → which bucket owns the object.
FEATURES_ROLES = (
    "feature_content",
    "feature_manifest",
    "rejected",
    "canonical_pack",
    "seal_receipt",
    "seal_file_sidecar",
    "package_inventory",
    "provenance_receipt",
    # tickets / pack / seal live with features bucket per CR4 storage contract
    "tickets",
)
LABEL_VAULT_ROLES = (
    "label_content",
    "label_manifest",
)

ROLE_TO_LOCKED_HASH_KEY: Mapping[str, str] = {
    "feature_content": "feature_content_sha256",
    "feature_manifest": "feature_manifest_sha256",
    "label_content": "label_content_sha256",
    "label_manifest": "label_manifest_sha256",
    "rejected": "rejected_sha256",
    "canonical_pack": "canonical_pack_sha256",
    "seal_receipt": "seal_file_sha256",
    "seal_file_sidecar": "seal_file_sha256",  # sidecar bytes are "<sha>\\n"
}

# Staging relative destinations for hydrated objects.
ROLE_STAGING_RELPATH: Mapping[str, str] = {
    "feature_content": "feature_package/features.json",
    "feature_manifest": "feature_package/feature_manifest.json",
    "label_content": "label_package/labels.json",
    "label_manifest": "label_package/label_manifest.json",
    "rejected": "rejected/rejected_events.json",
    "canonical_pack": "ncaam_official_schedule_2024_25.json",
    "seal_receipt": "seal/seal_receipt.json",
    "seal_file_sidecar": "seal/seal_receipt.file_sha256",
    "package_inventory": "inventory/package_inventory.json",
    "provenance_receipt": "inventory/provenance_receipt.json",
    "tickets": "tickets/tickets.json",
}


def cas_object_key(content_sha256: str, *, prefix: str = FROZEN_V1_1_CAS_PREFIX) -> str:
    """Content-addressed object key (exact frozen bytes under retention lock)."""
    digest = content_sha256.lower().strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError(f"invalid content sha256 for CAS key: {content_sha256!r}")
    return f"{prefix}{digest}"


def default_package_inventory() -> Dict[str, Any]:
    """Logical inventory CoS uploads after placing exact frozen v1.1 bytes.

    Hashes are locked; object keys are CAS placeholders until CoS fills upload status.
    """
    hashes = locked_expected_hashes()
    objects: List[Dict[str, Any]] = []
    for role, hash_key in ROLE_TO_LOCKED_HASH_KEY.items():
        if role == "seal_file_sidecar":
            # Sidecar file content is "<seal_file_sha256>\\n"; CAS key uses that file digest.
            # Placeholder until CoS computes sidecar-file digest after upload.
            sha = hashes["seal_file_sha256"]
            objects.append(
                {
                    "role": role,
                    "bucket": FEATURES_BUCKET,
                    "expected_content_sha256": sha,
                    "sidecar_text_sha256_of_seal_file": sha,
                    "cas_key": None,  # CoS fills after upload (sha256 of sidecar bytes)
                    "logical_path": ROLE_STAGING_RELPATH[role],
                    "upload_status": "PENDING_COS",
                    "retention": "indefinite",
                }
            )
            continue
        sha = hashes[hash_key]
        bucket = LABEL_VAULT_BUCKET if role in LABEL_VAULT_ROLES else FEATURES_BUCKET
        objects.append(
            {
                "role": role,
                "bucket": bucket,
                "expected_content_sha256": sha,
                "cas_key": cas_object_key(sha),
                "logical_path": ROLE_STAGING_RELPATH[role],
                "upload_status": "PENDING_COS",
                "retention": "indefinite",
            }
        )
    # Inventory + provenance are self-describing; CoS fills their CAS keys post-upload.
    for role in ("package_inventory", "provenance_receipt"):
        objects.append(
            {
                "role": role,
                "bucket": FEATURES_BUCKET,
                "expected_content_sha256": None,
                "cas_key": None,
                "logical_path": ROLE_STAGING_RELPATH[role],
                "upload_status": "PENDING_COS",
                "retention": "indefinite",
            }
        )
    return {
        "schema_version": "ncaam-holdout-package-inventory-v1",
        "holdout_id": "ncaam_holdout_2024_25_v1_1",
        "package_version": "v1.1",
        "phase": "2.6F-CR4",
        "authority": "private_r2_exact_frozen_bytes",
        "do_not_regenerate_substitutes": True,
        "features_bucket": FEATURES_BUCKET,
        "label_vault_bucket": LABEL_VAULT_BUCKET,
        "public_access": "disabled",
        "r2_dev_access": "disabled",
        "custom_domains": "none",
        "builders_receive_label_vault_credentials": False,
        "label_access": "governed_evaluator_after_explicit_unseal_only",
        "locked_expected_hashes": hashes,
        "objects": objects,
    }


def storage_contract_summary() -> Dict[str, Any]:
    return {
        "phase": "2.6F-CR4",
        "features_bucket": FEATURES_BUCKET,
        "label_vault_bucket": LABEL_VAULT_BUCKET,
        "features_env_placeholders": FEATURES_ENV,
        "label_vault_env_placeholders": LABEL_VAULT_ENV,
        "frozen_cas_prefix": FROZEN_V1_1_CAS_PREFIX,
        "inventory_key": FROZEN_V1_1_INVENTORY_KEY,
        "provenance_key": FROZEN_V1_1_PROVENANCE_KEY,
        "features_roles": list(FEATURES_ROLES),
        "label_vault_roles": list(LABEL_VAULT_ROLES),
        "locked_expected_hashes": locked_expected_hashes(),
        "credentials_in_git": False,
        "cloud_agent_upload_attempted": False,
        "cos_provisions_buckets_and_upload": True,
    }
