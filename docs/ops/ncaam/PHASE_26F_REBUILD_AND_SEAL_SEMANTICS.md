# NCAAM 2024–25 sealed holdout — rebuild / hydrate contract (Phase 2.6F CR4)

**No Odds API calls. No invented endpoints. No manual placement of sealed packages.**  
**CR4 LOCKED:** authoritative disaster recovery = exact frozen v1.1 bytes from private R2 (not raw+KenPom+odds rebuild).

## Authoritative sealed artifacts (CR4)

| Artifact                                                                          | Where                                                      | Exact ref                                                                                                           |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Feature content + manifest, rejected, pack, seal + sidecar, inventory, provenance | Private bucket `kosedge-ncaam-holdout-2425-features-v1`    | CAS under `ncaam/holdout_2024_25/v1_1/` — see `r2_object_refs` + `r2_storage_contract.py` (CoS fills upload status) |
| Label content + manifest                                                          | Private bucket `kosedge-ncaam-holdout-2425-label-vault-v1` | Labels ONLY; builders never receive vault credentials                                                               |
| Seal membership payload hash                                                      | `seal/seal_receipt.json` → `seal_payload_sha256`           | `af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84`                                                  |
| Seal on-disk file hash                                                            | `seal/seal_receipt.file_sha256`                            | `82852e2460bf876d75aae647232860820a998814b4bef76c236bdf058f0ddca2`                                                  |
| Feature / label content                                                           | Exact frozen bytes (not regenerated substitutes)           | `8c9e7fff…` / `aa7e1088…`                                                                                           |
| Feature / label manifests                                                         | `feature_package/` / `label_package/`                      | `f45c0438…` / `0893a9e2…`                                                                                           |
| Official schedule pack                                                            | Exact frozen bytes                                         | `4016f2ab4dcfbf713fdd005b4468ab5576345bea321caa59333685f224ae828e`                                                  |
| Rejected                                                                          | Exact frozen bytes                                         | `7adad293…`                                                                                                         |

**Bucket hardening (contract):** public access disabled; r2.dev disabled; no custom domains; indefinite retention locks on frozen v1.1 prefixes. CoS provisions/uploads — cloud agents must not invent credentials or upload.

Legacy ESPN raw (312 objects) remains in `kosedge-ncaam-lab-gap-recovery-raw-v1` for **forensic** reconstruction only.

## Recovery path B (clean checkout) — CR4 LOCKED

Enterprise path **B**: hydrate exact frozen packages from private R2 → staging → verify inventory + all locked hashes → reseal from downloaded packages with frozen v1.1 identity → release-pointer promote only after pass (immutable release dir + atomic `CURRENT` symlink switch).

```bash
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py --dry-run
python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py \
  --governed-evaluator --authorize-unseal
python scripts/ncaam/verify_2425_sealed_artifacts.py
```

Unit tests use `MockR2Store` (no network). Real hydrate is the script above after CoS upload.

### Determinism + release-pointer promote

1. Hashed identity uses **frozen v1.1 timestamps** — never `datetime.now()` in pack / manifest / seal membership.
2. Hydrate writes into a **staging** directory (live seal untouched; never unlink live seal first).
3. Staging verified against package inventory + locked expected hashes.
4. **Reseal** from downloaded content packages (real identity path); no silent reuse of a pre-seeded seal.
5. **Release-pointer promote** only after verification passes: materialize a complete immutable `releases/<id>/`, then atomically switch one `CURRENT` symlink (`os.replace` of the symlink). **No required writes after the pointer switch** (CR6) — no per-promotion compatibility-path rewrites. All governed consumers (including canonical pack) resolve one release through `CURRENT` via `active_release` / `resolve_live_artifacts`. Multi-file live `os.replace` is **not** an atomic promote.
6. On any mismatch/failure/interrupt **before** the pointer switch (including mid-materialize): refuse pointer switch and **preserve** the previous live package (all of features, labels, manifests, rejected, pack, seal). A reported failure must never claim `live_package_preserved=true` if `CURRENT` already moved.
7. Credential-free recovery receipt (no secrets in receipt or git).
8. Inventory SoT (`default_package_inventory` / CLI `_load_inventory`) proves 10/10 `UPLOADED` with non-null CAS keys. It does **not** expose per-object `provider_verified`; provider verification is tied separately to the sanitized provider retention receipt.

### CR7 — real consumer wiring (LOCKED)

After Path B promote, **one shared authoritative read API** owns the active release:

- Module: `apps/web/src/ncaam_lab/holdout_2425/active_release.py`
- Governed readers: verify script, coverage/phase26c auditors, builder pack read, evaluator inputs, feature/label/rejected/seal loaders
- Model-service `load_official_schedule_blob("2024-25")` **is** a holdout consumer: it resolves the pack through holdout `CURRENT`. The static `DATA_DIR/ncaam_official_schedule_2024_25.json` path is **not** the recovered canonical pack once `CURRENT` exists.
- Verifier **fails** when the authoritative canonical pack is unavailable (no soft note-only pass).
- CI forbid: `scripts/ncaam/check_active_release_flat_forbid.py` (+ pytest) blocks direct flat-constant authoritative reads in governed readers.

```bash
python scripts/ncaam/check_active_release_flat_forbid.py
python scripts/ncaam/verify_2425_sealed_artifacts.py
```

### Label vault separation

- Features hydrate: features-bucket credentials only.
- Labels hydrate: **separate** governed evaluator path after explicit unseal authorization.
- Builders calling label vault **fail closed** (tests prove this). Errors must not leak label contents.

### Fail-closed rules

- Missing feature object → fail closed; live preserved.
- Missing/restricted label object → fail closed; no label body in errors; live preserved.
- Corrupted object / wrong manifest or seal hash → fail closed; live preserved.
- Interrupted recovery / failed release-pointer promote → previous package preserved.
- No Odds API or live-data fallback.
- No regenerate-substitutes path for frozen holdout.

## Forensic path (NOT authoritative)

Raw + KenPom + odds reconstruction is a **separate forensic** path and must **not** redefine or promote the frozen holdout:

```bash
python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py --dry-run
python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py \
  --out-root /tmp/ncaam-forensic-2425
```

See also `docs/ops/ncaam/B1_DRIFT_FORENSIC_NOTE.md` (Alex owns event-level B1 receipts; do not change B1).

Deprecated: `rebuild_2425_sealed_holdout_from_governed_inputs.py` refuses promote and points here.

## Seal hash semantics (locked)

- `seal_payload_sha256`: SHA-256 of canonical seal JSON **before** inserting the hash field.
- `seal_file_sha256`: on-disk digest after the payload field is inserted (also sidecar).
- Frozen identity timestamps live in `apps/web/src/ncaam_lab/holdout_2425/locked_identity.py`.
- Storage contract: `apps/web/src/ncaam_lab/holdout_2425/r2_storage_contract.py`.

## KenPom PIT archive-date semantics (locked)

- Filename `kenpom_YYYY-MM-DD.parquet` date **is** the archive as-of (`archive_date_semantics=filename_date_is_as_of`).
- `captured_at` may be null **only** under that explicit policy.
- Game `PIT_ELIGIBLE` requires bridged home+away `team_norm` present with non-null AdjEM **and** AdjT.
