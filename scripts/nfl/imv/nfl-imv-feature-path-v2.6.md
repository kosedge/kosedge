# IMV local feature path v2.6 — 04fd87a1

Parent: `nfl-imv-feature-path-v2.5.md`. Frozen: v21 `05027146…`,
v22 `57a419b4…`, v23 `fe66b374…`, v24 `7c3f4dc7…`, v25 `582eb6ce…`.
**Do not edit those files.** New helper `nfl_imv_v26.py` binds the
real v3 41-column tuple.

Parity CLI:

```bash
python3 "$IMV/nfl_imv_v26.py" parity \
  --local "$OUT6/store/features.jsonl" \
  --prod-export "$IMV_PROD_EXPORT" \
  --week-cap 6 \
  --grade cert \
  --build-started "$(cat "$OUT6/BUILD_STARTED_UTC")"
```

`query_sha` must equal `b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0`.
`EXPORT.sha256` is required (file + meta). Build-start is required.
`PINNED_V3_COLUMNS` is SQL v3 lines 60–102. Do not author samples.
Do not run W7.
