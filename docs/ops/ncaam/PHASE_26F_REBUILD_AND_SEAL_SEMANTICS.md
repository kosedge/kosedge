# NCAAM 2024–25 sealed holdout — rebuild / hydrate contract (Phase 2.6F)

**No Odds API calls. No invented endpoints. No manual placement of sealed packages.**

## Authoritative sealed artifacts

| Artifact                          | Where                                                               | Exact ref                                                                                                                                |
| --------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| ESPN scoreboard raw (312 objects) | R2 bucket `kosedge-ncaam-lab-gap-recovery-raw-v1`                   | prefix `ncaam/holdout_2024_25/espn_schedule_raw_v1/` — see `r2_object_refs/r2_object_refs_v1.json` (`cas_index_sha256`, `n_objects=312`) |
| Seal membership payload hash      | `seal/seal_receipt.json` → `seal_payload_sha256`                    | `af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84`                                                                       |
| Seal on-disk file hash            | external sidecar `seal/seal_receipt.file_sha256` (or verify script) | historically `1074731f…` when key was still `seal_receipt_sha256`; recomputed after rename                                               |
| Features / labels bulk            | rebuilt from governed inputs (not git)                              | content sha in feature/label manifests                                                                                                   |
| Official schedule pack            | rebuilt from governed ESPN raw (path B)                             | `ncaam_official_schedule_2024_25.json`                                                                                                   |
| KenPom snapshots / odds parquet   | in-repo processed paths used by builder                             | `apps/web/data/processed/kenpom_snapshots`, `ncaab_historical_odds_open_close.parquet`                                                   |

## Recovery path B (clean checkout) — locked

Enterprise path **B**: deterministically rebuild sealed packages + canonical schedule pack from governed inputs. Manual placement of deferred schedule/seal artifacts is **rejected**.

1. Ensure PR B governance refs exist (`r2_object_refs_v1.json`).
2. Hydrate raw ESPN from locked R2 refs (only bytes not rebuildable from git):

```bash
python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --dry-run
python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --role espn_schedule_raw_v1
```

3. Rebuild schedule pack + sealed packages from governed inputs (fail-closed if raw / KenPom / odds missing):

```bash
python scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py --dry-run
python scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py
```

Equivalent decomposed steps:

```bash
python scripts/ncaam/ingest_espn_official_schedule.py --season 2024-25 \
  --from-raw-dir data/ops/lab/ncaam/holdout_2024_25/raw/espn_scoreboard
python scripts/ncaam/build_2425_sealed_holdout.py --season 2024-25
```

4. Verify:

```bash
python scripts/ncaam/verify_2425_sealed_artifacts.py --require-raw
```

### Fail-closed rules

- Builder refuses derived artifacts / sealing when `immutable_raw_preserved=false` (missing or mismatched sha256 sidecars).
- Rebuild refuses if ESPN raw, KenPom snapshots, or odds parquet are absent.
- Soft-green continuation after raw integrity failure is a defect.

## Seal hash semantics (locked)

- `seal_payload_sha256`: SHA-256 of canonical seal JSON **before** inserting the hash field (membership identity).
- `seal_file_sha256`: on-disk digest after the payload field is inserted (also `seal/seal_receipt.file_sha256`).
- Internal build/readiness consumers use these explicit fields only.
- `seal_receipt_sha256` may appear only as an explicitly labeled compatibility alias equal to `seal_payload_sha256` (external readers). Do **not** treat it as the file digest.
- Do **not** claim the payload hash equals the file hash.

## KenPom PIT archive-date semantics (locked)

- Filename `kenpom_YYYY-MM-DD.parquet` date **is** the archive as-of (`archive_date_semantics=filename_date_is_as_of`).
- `captured_at` may be null **only** under that explicit policy (`null_captured_at_policy=allowed_when_filename_date_is_as_of`).
- `require_captured_at=True` refuses null.
- Game `PIT_ELIGIBLE` requires bridged home+away `team_norm` present with non-null AdjEM **and** AdjT.
