# NCAAM 2024–25 sealed holdout — rebuild / hydrate contract (Phase 2.6F)

**No Odds API calls. No invented endpoints. No manual placement of sealed packages.**

## Authoritative sealed artifacts

| Artifact                          | Where                                                               | Exact ref                                                                                                                                |
| --------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| ESPN scoreboard raw (312 objects) | R2 bucket `kosedge-ncaam-lab-gap-recovery-raw-v1`                   | prefix `ncaam/holdout_2024_25/espn_schedule_raw_v1/` — see `r2_object_refs/r2_object_refs_v1.json` (`cas_index_sha256`, `n_objects=312`) |
| Seal membership payload hash      | `seal/seal_receipt.json` → `seal_payload_sha256`                    | `af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84`                                                                       |
| Seal on-disk file hash            | external sidecar `seal/seal_receipt.file_sha256` (or verify script) | `82852e2460bf876d75aae647232860820a998814b4bef76c236bdf058f0ddca2` (legacy key era: `1074731f…`)                                         |
| Feature / label content           | rebuilt from governed inputs (not git)                              | `8c9e7fff…` / `aa7e1088…`                                                                                                                |
| Feature / label manifests         | `feature_package/` / `label_package/`                               | `f45c0438…` / `0893a9e2…`                                                                                                                |
| Official schedule pack            | rebuilt from governed ESPN raw (path B)                             | `ncaam_official_schedule_2024_25.json` sha256 `4016f2ab4dcfbf713fdd005b4468ab5576345bea321caa59333685f224ae828e`                         |
| KenPom snapshots / odds parquet   | in-repo processed paths used by builder                             | `apps/web/data/processed/kenpom_snapshots`, `ncaab_historical_odds_open_close.parquet`                                                   |

## Recovery path B (clean checkout) — locked

Enterprise path **B**: deterministically rebuild sealed packages + canonical schedule pack from governed inputs. Manual placement of deferred schedule/seal artifacts is **rejected**.

### Determinism + atomic promote (CR3)

1. Hashed identity uses **frozen v1.1 timestamps** (`sealed_at` / pack `as_of`) — never `datetime.now()` in pack / manifest / seal membership.
2. Rebuild writes into a **staging** directory (live seal untouched).
3. Staging is verified against locked expected hashes (pack + content + manifests + seal payload/file).
4. **Atomic promote** (`os.replace`) only after verification passes; seal is promoted last.
5. On any mismatch/failure: refuse promotion and **preserve** the previous live seal.
6. **CR3(b) proof:** tip content bytes (features/labels/rejected/pack) asserted equal to locked content/pack hashes, then manifests+seal rebuilt via `reseal_from_content_packages` (real identity path) and checked with `locked_expected_hashes()`. Live `ingest_window` `datetime.now` does **not** affect Path B `ingest_from_raw_dir` hashed pack when as_of is frozen.

```bash
python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --dry-run
python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --role espn_schedule_raw_v1
python scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py --dry-run
python scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py
python scripts/ncaam/verify_2425_sealed_artifacts.py --require-raw
```

### Fail-closed rules

- Builder refuses derived artifacts / sealing when `immutable_raw_preserved=false` (missing or mismatched sha256 sidecars).
- Rebuild refuses if ESPN raw, KenPom snapshots, or odds parquet are absent.
- Rebuild refuses promotion when staging hashes ≠ locked v1.1 expectations.
- Soft-green continuation after raw integrity failure is a defect.

## Seal hash semantics (locked)

- `seal_payload_sha256`: SHA-256 of canonical seal JSON **before** inserting the hash field (membership identity).
- `seal_file_sha256`: on-disk digest after the payload field is inserted (also `seal/seal_receipt.file_sha256`).
- Internal build/readiness consumers use these explicit fields only.
- `seal_receipt_sha256` may appear only as an explicitly labeled compatibility alias equal to `seal_payload_sha256` (external readers). Do **not** treat it as the file digest.
- Do **not** claim the payload hash equals the file hash.
- Frozen identity timestamps live in `apps/web/src/ncaam_lab/holdout_2425/locked_identity.py`.

## KenPom PIT archive-date semantics (locked)

- Filename `kenpom_YYYY-MM-DD.parquet` date **is** the archive as-of (`archive_date_semantics=filename_date_is_as_of`).
- `captured_at` may be null **only** under that explicit policy (`null_captured_at_policy=allowed_when_filename_date_is_as_of`).
- `require_captured_at=True` refuses null.
- Game `PIT_ELIGIBLE` requires bridged home+away `team_norm` present with non-null AdjEM **and** AdjT.
