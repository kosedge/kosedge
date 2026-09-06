# NCAAM 2024–25 sealed holdout — rebuild / hydrate contract (Phase 2.6F)

**No Odds API calls. No invented endpoints.**

## Authoritative sealed artifacts

| Artifact                          | Where                                                               | Exact ref                                                                                                                                |
| --------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| ESPN scoreboard raw (312 objects) | R2 bucket `kosedge-ncaam-lab-gap-recovery-raw-v1`                   | prefix `ncaam/holdout_2024_25/espn_schedule_raw_v1/` — see `r2_object_refs/r2_object_refs_v1.json` (`cas_index_sha256`, `n_objects=312`) |
| Seal membership payload hash      | `seal/seal_receipt.json` → `seal_payload_sha256`                    | `af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84`                                                                       |
| Seal on-disk file hash            | external sidecar `seal/seal_receipt.file_sha256` (or verify script) | historically `1074731f…` when key was still `seal_receipt_sha256`; recomputed after rename                                               |
| Features / labels bulk            | deferred / not git (hashes in manifests)                            | content sha in feature/label manifests                                                                                                   |
| Official schedule pack            | deferred / not git OR local model-service path                      | `ncaam_official_schedule_2024_25.json`                                                                                                   |
| KenPom snapshots / odds parquet   | local processed paths used by builder                               | `apps/web/data/processed/kenpom_snapshots`, `ncaab_historical_odds_open_close.parquet`                                                   |

## Rebuild path (clean checkout)

1. Ensure PR B governance refs exist (`r2_object_refs_v1.json`).
2. Hydrate raw ESPN from locked R2 refs:

```bash
python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --dry-run
python scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py --role espn_schedule_raw_v1
```

3. Place deferred schedule pack + processed KenPom/odds inputs (hashes recorded in manifests / deferred ledger).
4. Rebuild sealed package:

```bash
python scripts/ncaam/build_2425_sealed_holdout.py --season 2024-25
```

5. Verify:

```bash
python scripts/ncaam/verify_2425_sealed_artifacts.py --require-raw
```

## Seal hash semantics (locked)

- `seal_payload_sha256`: SHA-256 of canonical seal JSON **before** inserting the hash field (membership identity).
- On-disk file digest **differs** after the field is inserted; record it externally (`seal_receipt.file_sha256` / build summary `seal_file_sha256`).
- Do **not** claim the payload hash equals the file hash.

## KenPom PIT archive-date semantics (locked)

- Filename `kenpom_YYYY-MM-DD.parquet` date **is** the archive as-of (`archive_date_semantics=filename_date_is_as_of`).
- `captured_at` may be null **only** under that explicit policy (`null_captured_at_policy=allowed_when_filename_date_is_as_of`).
- `require_captured_at=True` refuses null.
- Game `PIT_ELIGIBLE` requires bridged home+away `team_norm` present with non-null AdjEM **and** AdjT.
