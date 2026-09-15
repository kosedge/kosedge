# CFB 2026 W−1 raw unadjusted team-game metrics

Research-only. **Not KE Ratings.** `opponent_adjusted=false`.

- as_of: `20260915`
- as_of_week: `3`
- eligible games: `85`
- table rows: `170`
- validation passed: `True`

Checks:
- `zero_unfinished_rows`: PASS
- `included_count_equals_manifest_eligible`: PASS
- `leakage_week_lt_as_of`: PASS
- `kickoff_week_contract`: PASS
- `opponent_adjusted_false_all_rows`: PASS
- `input_sha_recorded`: PASS
- `no_historical_lake_write`: PASS
- `not_labeled_ke_ratings`: PASS
- `cfbd_unused`: PASS

Bulk parquet lives in the gitignored as_of folder.
HD target: `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/`.
