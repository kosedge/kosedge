"""Private R2 storage contract for frozen v1.1 holdout disaster recovery (Phase 2.6F CR4/CR5).

CoS provisioned buckets and uploaded exact frozen bytes (verified PASS, fresh-download).
This module is the single source of truth for package inventory object entries.
Checked-in `r2_object_refs/r2_object_refs_v1.json` package_inventory.objects MUST
match `default_package_inventory()["objects"]` fingerprints (generated+verified).

Env var *names* only — no credentials, secrets, or agent-side uploads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from ncaam_lab.holdout_2425.locked_identity import locked_expected_hashes

# Cloudflare R2 account id (public identifier; not a secret).
R2_ACCOUNT_ID = "29e153aea94d9d3394f523bc9a3938cf"

# Separate private buckets (public access + r2.dev disabled; no custom domains).
FEATURES_BUCKET = "kosedge-ncaam-holdout-2425-features-v1"
LABEL_VAULT_BUCKET = "kosedge-ncaam-holdout-2425-label-vault-v1"

# Retention lock rule names (provider-side; CoS applied).
FEATURES_RETENTION_LOCK = "retain-holdout-2425-features-v1"
LABEL_VAULT_RETENTION_LOCK = "retain-holdout-2425-label-vault-v1"

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

# Uploaded object digests for roles not covered by locked_expected_hashes().
# Sidecar *file* bytes are "<seal_file_sha256>\\n"; CAS digests those bytes.
SEAL_FILE_SIDECAR_FILE_SHA256 = (
    "aa3e148703a5e23d5f82a9a74d143bb97d3e0c8b053754965f9de464d76967d8"
)
PACKAGE_INVENTORY_CONTENT_SHA256 = (
    "51bc1ed2dd23e439d0f06d8f2602dae62555474edaf986866959eb6229590a5b"
)
PROVENANCE_RECEIPT_CONTENT_SHA256 = (
    "25f2fc6e1c1cd8bb81b95ec84e867c315233f6ac9af7080b94a97cf1f18b8f19"
)

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
    "seal_file_sidecar": "seal_file_sha256",  # sidecar TEXT names seal_file_sha256
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
    """Logical inventory of CoS-uploaded exact frozen v1.1 bytes (UPLOADED).

    Hashes are locked; cas_keys are the verified R2 CAS object keys under the
    contract prefix. Recovery MUST use these keys only — orphan paths under
    cas/sha256/* or logical/v1_1/* are non-authoritative.
    """
    hashes = locked_expected_hashes()
    objects: List[Dict[str, Any]] = []
    for role, hash_key in ROLE_TO_LOCKED_HASH_KEY.items():
        if role == "seal_file_sidecar":
            # Sidecar file content is "<seal_file_sha256>\\n".
            # expected_content_sha256 names the seal-file digest (sidecar TEXT);
            # CAS / sidecar_file_sha256 digests the sidecar file bytes.
            seal_sha = hashes["seal_file_sha256"]
            objects.append(
                {
                    "role": role,
                    "bucket": FEATURES_BUCKET,
                    "expected_content_sha256": seal_sha,
                    "sidecar_text_sha256_of_seal_file": seal_sha,
                    "sidecar_file_sha256": SEAL_FILE_SIDECAR_FILE_SHA256,
                    "cas_key": cas_object_key(SEAL_FILE_SIDECAR_FILE_SHA256),
                    "logical_path": ROLE_STAGING_RELPATH[role],
                    "upload_status": "UPLOADED",
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
                "upload_status": "UPLOADED",
                "retention": "indefinite",
            }
        )
    # Inventory + provenance: fixed logical keys + CAS copies (both in features bucket).
    for role, content_sha, fixed_key in (
        (
            "package_inventory",
            PACKAGE_INVENTORY_CONTENT_SHA256,
            FROZEN_V1_1_INVENTORY_KEY,
        ),
        (
            "provenance_receipt",
            PROVENANCE_RECEIPT_CONTENT_SHA256,
            FROZEN_V1_1_PROVENANCE_KEY,
        ),
    ):
        objects.append(
            {
                "role": role,
                "bucket": FEATURES_BUCKET,
                "expected_content_sha256": content_sha,
                "cas_key": cas_object_key(content_sha),
                "fixed_key": fixed_key,
                "logical_path": ROLE_STAGING_RELPATH[role],
                "upload_status": "UPLOADED",
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
        "r2_account_id": R2_ACCOUNT_ID,
        "features_bucket": FEATURES_BUCKET,
        "label_vault_bucket": LABEL_VAULT_BUCKET,
        "features_retention_lock": FEATURES_RETENTION_LOCK,
        "label_vault_retention_lock": LABEL_VAULT_RETENTION_LOCK,
        "public_access": "disabled",
        "r2_dev_access": "disabled",
        "custom_domains": "none",
        "builders_receive_label_vault_credentials": False,
        "label_access": "governed_evaluator_after_explicit_unseal_only",
        "cos_upload_status": "UPLOADED_VERIFIED_PASS",
        "cos_upload_verification": "fresh_download_sha256_match",
        "authoritative_cas_prefix": FROZEN_V1_1_CAS_PREFIX,
        "orphan_non_authoritative_prefixes": [
            "cas/sha256/",
            "logical/v1_1/",
        ],
        "locked_expected_hashes": hashes,
        "objects": objects,
    }


def storage_contract_summary() -> Dict[str, Any]:
    return {
        "phase": "2.6F-CR4",
        "r2_account_id": R2_ACCOUNT_ID,
        "features_bucket": FEATURES_BUCKET,
        "label_vault_bucket": LABEL_VAULT_BUCKET,
        "features_retention_lock": FEATURES_RETENTION_LOCK,
        "label_vault_retention_lock": LABEL_VAULT_RETENTION_LOCK,
        "features_env_placeholders": FEATURES_ENV,
        "label_vault_env_placeholders": LABEL_VAULT_ENV,
        "frozen_cas_prefix": FROZEN_V1_1_CAS_PREFIX,
        "inventory_key": FROZEN_V1_1_INVENTORY_KEY,
        "provenance_key": FROZEN_V1_1_PROVENANCE_KEY,
        "features_roles": list(FEATURES_ROLES),
        "label_vault_roles": list(LABEL_VAULT_ROLES),
        "locked_expected_hashes": locked_expected_hashes(),
        "seal_file_sidecar_file_sha256": SEAL_FILE_SIDECAR_FILE_SHA256,
        "package_inventory_content_sha256": PACKAGE_INVENTORY_CONTENT_SHA256,
        "provenance_receipt_content_sha256": PROVENANCE_RECEIPT_CONTENT_SHA256,
        "credentials_in_git": False,
        "cloud_agent_upload_attempted": False,
        "cos_provisions_buckets_and_upload": True,
        "cos_buckets_provisioned": True,
        "cos_upload_status": "UPLOADED_VERIFIED_PASS",
        "cos_upload_verification": "fresh_download_sha256_match",
        "orphan_non_authoritative_prefixes": [
            "cas/sha256/",
            "logical/v1_1/",
        ],
    }
