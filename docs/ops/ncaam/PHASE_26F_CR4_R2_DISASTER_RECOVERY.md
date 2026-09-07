# Phase 2.6F CR4 — private R2 disaster recovery (ops)

**Status:** CoS PROVISIONED + UPLOADED (verified PASS, fresh-download) — do not merge; #490/#491/#496/#497 untouched  
**Decision locked:** restore exact frozen v1.1 packages from private retention-locked R2.  
Raw+KenPom+odds reconstruction is a **separate forensic** path and must not redefine the frozen holdout.

## Storage contract (CoS provisioned + uploaded; no secrets in git)

| Item                      | Value                                                                                           |
| ------------------------- | ----------------------------------------------------------------------------------------------- |
| R2 account id             | `29e153aea94d9d3394f523bc9a3938cf` (not a secret)                                               |
| Features bucket           | `kosedge-ncaam-holdout-2425-features-v1`                                                        |
| Label vault bucket        | `kosedge-ncaam-holdout-2425-label-vault-v1`                                                     |
| Public access             | disabled                                                                                        |
| r2.dev                    | disabled                                                                                        |
| Custom domains            | none                                                                                            |
| Retention                 | indefinite locks (`retain-holdout-2425-features-v1`, `retain-holdout-2425-label-vault-v1`)      |
| CoS upload status         | **UPLOADED** — fresh-download sha256 match (PASS)                                               |
| Builder label-vault creds | **never**                                                                                       |
| Label access              | governed evaluator after explicit unseal only                                                   |
| Object layout             | content-addressed (`ncaam/holdout_2024_25/v1_1/cas/<sha256>`) + fixed inventory/provenance keys |

Governed object set (all `upload_status=UPLOADED` in `default_package_inventory()`): features+manifest, labels+manifest, rejected, canonical pack, seal receipt + file-hash sidecar, package inventory + provenance receipt.

Env placeholders (**names only** — never commit key values): see `r2_storage_contract.FEATURES_ENV` / `LABEL_VAULT_ENV`.

### Authoritative CAS keys

Recovery **MUST** use contract keys from `r2_storage_contract.default_package_inventory()` only.

An earlier mistaken upload under `cas/sha256/*` and `logical/v1_1/*` may remain as orphans under retention lock; those paths are **non-authoritative**. Do not hydrate from them.

Fixed logical keys (features bucket), also mirrored under CAS:

- `ncaam/holdout_2024_25/v1_1/package_inventory.json` (+ `cas/51bc1ed2…`)
- `ncaam/holdout_2024_25/v1_1/provenance_receipt.json` (+ `cas/25f2fc6e…`)

Seal sidecar: CAS digests file bytes `"<seal_file_sha256>\\n"` (`aa3e1487…`); `expected_content_sha256` remains the seal-file digest (`82852e24…`).

## Recovery entrypoint

```bash
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py --print-contract
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py --dry-run
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py \
  --governed-evaluator --authorize-unseal
```

Flow: hydrate → staging → verify inventory+locked hashes → reseal (frozen v1.1 identity) → **release-pointer promote** (materialize immutable `releases/<id>/`, then atomically switch single `CURRENT` symlink; **no required writes after the switch** — CR6). Live seal never unlinked first. Multi-file live `os.replace` is **not** atomic and is not used for cutover. Credential-free receipt. Python `default_package_inventory()` / CLI `_load_inventory()` is SoT for 10/10 `UPLOADED` + non-null CAS keys (checked-in refs JSON must match); it does **not** itself expose per-object `provider_verified` — that belongs on the sanitized provider retention receipt.

## Forensic (non-authoritative)

```bash
python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py --dry-run
```

B1 drift investigation ownership: `docs/ops/ncaam/B1_DRIFT_FORENSIC_NOTE.md` (Alex).  
Forensic finding supports CR4: raw rebuild cannot redefine frozen v1.1 (no B1/threshold/membership changes).

## Locked hashes

See `locked_identity.locked_expected_hashes()` — feature/label content+manifest, rejected, seal payload/file, canonical pack.
