# Prod feature export spec (v2.4 / 47616a70 + v3 SQL)

Parent: `nfl-imv-prod-export-spec-v2.3.md`. v2.4 **adds** C-4 fields.
Parity is **NOT_RUN_NO_PROD_EXPORT** until a genuine sealed export is
supplied. Do **not** author samples.

Reader SQL is **v3** at `ops/platform/PR_PROD_PARITY_EXPORT_v3.sql`,
pin `b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0`.
Missing file or sha mismatch → `NOT_RUN`. 41-column CSV.
`roof_vocab_unknown` is an audit column. Rest raw + derived.

## Required `EXPORT.meta.json`

```json
{
  "kind": "sealed_prod_feature_export",
  "source": "railway-prod / nfl_dp_matchup_features_weekly",
  "query": "<exact SQL that produced features.jsonl>",
  "query_sha": "<sha256 of the query string>",
  "sha256": "<sha256 of features.jsonl>",
  "weeks": [3, 4, 5, 6, 7],
  "columns": ["season", "week", "game_id", "home_team", "away_team", "..."],
  "captured_utc": "2026-10-22T12:00:00Z",
  "data_as_of": "2026-10-22T12:00:00Z",
  "captured_by": "platform-reliability|ryan",
  "window_sql": "ROWS BETWEEN 4 PRECEDING AND CURRENT ROW",
  "db": "production warehouse (not reconstructed)"
}
```

Missing `captured_utc`, `data_as_of`, or `query_sha` →
`NOT_RUN_NO_PROD_EXPORT`. `query_sha` must equal sha256(`query`).
`captured_utc` **after** the feature `BUILD_STARTED_UTC` →
`FAIL_EXPORT_CAPTURED_AFTER_BUILD`.

Columns are the v3 SELECT list only (not v1). Weeks 3–7. Include rest
raw + derived, roof + `roof_vocab_unknown`, and `diff_off_epa_5g`.

```bash
export IMV_PROD_EXPORT=/abs/genuine-sealed-prod-export
python3 /var/tmp/nfl-imv-bundle-v24/nfl_imv_v24.py parity \
  --local "$OUT6/store/features.jsonl" \
  --prod-export "$IMV_PROD_EXPORT" \
  --week-cap 6 \
  --grade cert \
  --build-started "$(cat "$OUT6/BUILD_STARTED_UTC")"
```
