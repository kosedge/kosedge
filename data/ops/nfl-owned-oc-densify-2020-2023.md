# NFL Owned Open/Close Densify (2020–2023)

Generated: 2026-07-28  
Script: `scripts/nfl/densify_owned_oc_2020_2023.py`  
Spend: **6,022** credits · Remaining: **~2,993,254**

## Coverage by season (games with odds_snapshots)

| Season | Games w/ odds | Owned OC (grading join) |
| --- | ---: | ---: |
| 2020 | 276 | 237 |
| 2021 | 291 | 240 |
| 2022 | 283 | 241 |
| 2023 | 273 | 256 |
| 2024 | 266 | 229 |
| 2025 | 320 | 235 |

**Owned open/close games (grading):** 724 → **1,868**

## CLV sample (before → after densify)

| Metric | Before | After densify |
| --- | ---: | ---: |
| n_clv_spread | 159 | **494** |
| CLV spread +rate | 66.0% | 51.8% |
| CLV spread avg | +2.02 | +1.04 |
| n_clv_total | 117 | **279** |

Hundreds+ CLV n achieved. +rate diluted vs 2024–25-only dense sample — expected when
adding earlier seasons; do not treat the old 66% as the product bar.

## Notes

- Restored missing `scripts/odds/persist_mainline_odds.py` from commit `7bab07a7`.
- Cleared stale `nfl:mainlines` checkpoint phase after restore-swap lost prior densify writes.
- Props skipped (`--skip-props`).
