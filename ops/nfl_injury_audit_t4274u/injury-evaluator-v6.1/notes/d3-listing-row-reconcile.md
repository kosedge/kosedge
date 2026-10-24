# D-3 — 58653 vs 56537 listing rows (2116)

Ruling `e7a0d737`: the C-3 raw census counted **58653** rows in
`/tmp/injury-fit-raw-le2023/listings/listings_2013.csv` … `listings_2023.csv`.
Path 1 `run.stdout.txt` reported `n_listing_rows=56537`. Difference **2116**.

## Reason

Frozen `load_listings()` at script `8d188da2`
(`/cursor/stores/self/artifacts/injury-fit-le2023/run_injury_residual_fit.py`
L259–287) keeps a row only when
`str(row.get("game_type") or "REG").upper() == "REG"` and `year in FIT_YEARS`
(2013–2023). Non-REG rows are skipped. Week-parse failures: 0. Year-not-in-fit:
0. Holdout seasons: 0 (no 2024/25 file opened).

## Counts by `game_type` (all 58653 raw rows)

| game_type | n | fate |
|---|---|---|
| REG | **56537** | kept (`n_listing_rows`) |
| WC | 1010 | dropped |
| DIV | 669 | dropped |
| CON | 324 | dropped |
| SB | 113 | dropped |
| **total** | **58653** | |
| **dropped** | **2116** | 1010+669+324+113 |

`56537 + 2116 = 58653`. No leftover.

POST/PRE/empty: 0 in these files. Every dropped row is playoff
(`WC`/`DIV`/`CON`/`SB`). The C-3 format census (all `Z`) was over the full
raw files, including those 2116 playoff rows. The fit and the export use the
REG 56537 only. Neither set contains a naive `date_modified`.
