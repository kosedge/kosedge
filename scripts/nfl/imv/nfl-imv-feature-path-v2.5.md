# IMV local feature path v2.5 — 54ba672b

Parent: `nfl-imv-feature-path-v2.4.md`. Frozen: v21 `05027146…`,
v22 `57a419b4…`, v23 `fe66b374…`, v24 `7c3f4dc7…`. **Do not edit those
files.** New helper `nfl_imv_v25.py` closes R-1..R-9 and C-3/C-4.

Parity CLI:

```bash
python3 "$IMV/nfl_imv_v25.py" parity \
  --local "$OUT6/store/features.jsonl" \
  --prod-export "$IMV_PROD_EXPORT" \
  --week-cap 6 \
  --grade cert \
  --build-started "$(cat "$OUT6/BUILD_STARTED_UTC")"
```

`query_sha` must equal `b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0`.
`EXPORT.meta.json` must include `sha256`. Build-start is required.
Output carries `evidence_label=REPORTED`. Plumbing status is
`PASS_PLUMBING` and is not cert. Do not author samples. Do not run W7.
