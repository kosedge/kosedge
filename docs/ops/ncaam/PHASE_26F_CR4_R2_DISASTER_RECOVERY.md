# Phase 2.6F CR4 — private R2 disaster recovery (ops)

**Status:** IMPLEMENTATION — do not merge; #490/#491/#496/#497 untouched  
**Decision locked:** restore exact frozen v1.1 packages from private retention-locked R2.  
Raw+KenPom+odds reconstruction is a **separate forensic** path and must not redefine the frozen holdout.

## Storage contract (CoS provisions; no secrets in git)

| Item                      | Value                                                  |
| ------------------------- | ------------------------------------------------------ |
| Features bucket           | `kosedge-ncaam-holdout-2425-features-v1`               |
| Label vault bucket        | `kosedge-ncaam-holdout-2425-label-vault-v1`            |
| Public access             | disabled                                               |
| r2.dev                    | disabled                                               |
| Custom domains            | none                                                   |
| Retention                 | indefinite locks on frozen v1.1 prefixes               |
| Builder label-vault creds | **never**                                              |
| Label access              | governed evaluator after explicit unseal only          |
| Object layout             | content-addressed (`cas/<sha256>`) + logical manifests |

Governed object set: features+manifest, labels+manifest, rejected, canonical pack, seal receipt + file-hash sidecar, package inventory + provenance receipt.

Env placeholders (names only): see `r2_storage_contract.FEATURES_ENV` / `LABEL_VAULT_ENV`.

## Recovery entrypoint

```bash
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py --print-contract
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py --dry-run
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py \
  --governed-evaluator --authorize-unseal
```

Flow: hydrate → staging → verify inventory+locked hashes → reseal (frozen v1.1 identity) → atomic promote. Live seal never unlinked first. Credential-free receipt.

## Forensic (non-authoritative)

```bash
python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py --dry-run
```

B1 drift investigation ownership: `docs/ops/ncaam/B1_DRIFT_FORENSIC_NOTE.md` (Alex).

## Locked hashes

See `locked_identity.locked_expected_hashes()` — feature/label content+manifest, rejected, seal payload/file, canonical pack.
