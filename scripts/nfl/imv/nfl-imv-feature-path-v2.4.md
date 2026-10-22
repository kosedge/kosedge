# IMV local feature path v2.4 — 47616a70

v2.3 plumbing stands. This addendum is **C-1..C-6** plus the returned Mac
runbook. Frozen helpers: `nfl_imv_v22.py` = `57a419b4…`, `nfl_imv_v23.py`
= `fe66b374…`. **Do not edit those files.** Parent:
`nfl-imv-feature-path-v2.3.md`. **Do not run W7.** Do not copy scripts
into `$BASE/scripts`.

## C-1 zero matched rows

Parity with an export and **zero** local↔prod team-week joins is
`FAIL_ZERO_MATCHED_ROWS`, not PASS.

## C-2 10 of 14 + separate checks

Only these 10 keys use local week W vs prod week W−1 by team:

`home/away` × `off_epa_5g`, `def_epa_allowed_5g`, `pass_rate_5g`,
`success_offense_5g`, `pressure_allowed_5g`.

The other 4 of the v2.2 14 are **separate same-game** checks
(`c57032db`): `home_rest_days`, `away_rest_days`, `roof_dome` (exact);
`diff_off_epa_5g` must equal `home_off_epa_5g − away_off_epa_5g`.

## C-3 cert vs plumbing tolerances

| Grade    | 10 team-form keys | Use                          |
| -------- | ----------------- | ---------------------------- |
| plumbing | 0.02 / 0.03       | v2.3 `PARITY_TOLERANCES`     |
| cert     | **0.005**         | pre-registered; default PASS |

Cert PASS (`c57032db`): zero out-of-tolerance **and** ≥1 matched
team-week **and** ≥90% coverage **and** 100% on separate-check keys.

## C-4 export provenance

`EXPORT.meta.json` must include `captured_utc`, `data_as_of`, and
`query_sha` (sha256 of `query`). An export captured **after**
`BUILD_STARTED_UTC` is `FAIL_EXPORT_CAPTURED_AFTER_BUILD`.

## C-5 helper pins

| File             | Pin (sha256)                                                       |
| ---------------- | ------------------------------------------------------------------ |
| `nfl_imv_v21.py` | `050271467cd38f5a174043c67f2df9622d7f0b8125f137b822f888846f4c561f` |
| `nfl_imv_v22.py` | `57a419b42f743dafb590d3dff8b40b7f89769db04d38ce2f48453bc0f85b1843` |
| `nfl_imv_v23.py` | `fe66b374905817b1e991bc7260554dc8c706d8a487baf4876bc04bc1436d0470` |

Mismatch → BLOCK. Bundle also copies these files plus feature-path docs
and `README.md` into `OUT/bundle` (and the seal).

## C-6 SHA256SUMS last

After helper stamps land in `OUT/store`, `write_store_sha256sums_last`
rewrites `SHA256SUMS`. Nothing in the store is written after that file.

## IMV folder (returned)

Helpers run from a **sha-checked directory outside BASE**. Never
`IMV="$BASE/scripts/nfl/imv"`. The builder/runner refuse that layout.
