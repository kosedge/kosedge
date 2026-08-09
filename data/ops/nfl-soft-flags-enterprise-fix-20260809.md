# NFL Soft Flags — Enterprise Fix

Date: 20260809  
Engine: `nfl-season-engine-v1.23-soft-flags-enterprise`  
Base: Step-3 review board (`nfl-preseason-sim-2026-20260809T144255Z`)  
Fix board: `nfl-preseason-sim-2026-20260809T150233Z`  
Smoke review bundle / web pointer: `nfl-preseason-sim-2026-20260809T150309Z`  

## Status

**NOT LOCKED**

Do not treat this as a production lock. No final-lock tag.

## CIN (critical)

| | Value |
|--|------:|
| Pass yards (locked) | 5119.1 |
| PF | 437.7 |
| PA | 424.5 |
| Wins | 9.47 |
| Burrow pass yds | 4813.1 |
| Burrow pass TDs | 38.25 |

## Top RBs (differentiated soft priors)

| Rank | Player | Team | Rush yds | Rush TDs |
|-----:|--------|------|---------:|---------:|
| 1 | James Cook III | BUF | 1479 | 10.9 |
| 2 | Kyren Williams | LA | 1459 | 11.0 |
| 3 | Derrick Henry | BAL | 1442 | 11.0 |
| 4 | Bijan Robinson | ATL | 1441 | 10.1 |
| 5 | Javonte Williams | DAL | 1439 | 10.8 |
| 6 | Jacory Croskey-Merritt | WAS | 1435 | 10.4 |
| 7 | Zach Charbonnet | SEA | 1427 | 10.8 |
| 8 | Rhamondre Stevenson | NE | 1419 | 10.5 |
| 9 | Cam Skattebo | NYG | 1415 | 10.0 |
| 10 | Saquon Barkley | PHI | 1410 | 10.5 |
| 11 | Bucky Irving | TB | 1403 | 10.2 |
| 12 | Christian McCaffrey | SF | 1402 | 10.7 |

## Wins / PF

| Metric | Value |
|--------|------:|
| Wins min / max / range | 3.74 / 12.60 / 8.86 |
| Wins Σ | 272.00 |
| Max win-value tie count | 6 |
| PF min / max / range | 282.6 / 481.0 / 198.4 |
| League PF / PA | 11859.2 / 11859.2 |
| Max PF-value tie count | 8 |

## Conservation

| Check | Value |
|-------|------:|
| Pass pool | 125998.1 |
| Rush pool | 64000.0 |
| ARI/BAL/SEA pass | {'ARI': 4350.4, 'BAL': 3578.6, 'SEA': 4258.5} |

## Labeling fixes

- Kyler Murray: MIN→ARI (was Jacoby Brissett on ARI QB1)
- J.J. McCarthy: MIN→MIN (was Jacoby Brissett on MIN QB1)
- Michael Penix Jr.: ATL→ATL (was Tua Tagovailoa on ATL QB1)
- Tua Tagovailoa: ATL→MIA (was Malik Willis on MIA QB1)

## Gates

| Check | Result |
|-------|--------|
| league_pf_pa_11859 | **PASS** |
| wins_sum_272 | **PASS** |
| win_range_ge_7_5 | **PASS** |
| pass_pool_locked | **PASS** |
| rush_pool_64000 | **PASS** |
| ari_bal_sea_pass_untouched | **PASS** |
| cin_not_bottom_tier | **PASS** |
| cin_wins_band_9_12 | **PASS** |
| rb_top12_differentiated | **PASS** |
| top_rb_ge_1400 | **PASS** |
| pf_cluster_lt_12 | **PASS** |
| win_ties_improved | **PASS** |
| offense_smoke | **PASS** |
| defense_smoke | **PASS** |
| kyler_on_ari | **PASS** |
| **ALL** | **PASS** |

## Method
1. High-volume (≥4600 pass yds) min ~5.1% pass-TD rate + PF points-per-attempt floor (~0.50)
2. RB hard floor → soft prior (~1380) + team-rush rank / prior residual / OL proxy; rush Σ=64k
3. PF/PA stretch: tapered band penalties (no hard clips), softer intensity, renorm PF=PA≈11859, wins Σ=272
4. QB label hygiene (identity swap; team pools untouched)
5. Smoke only — **NOT LOCKED**
