# NFL Soft Piles Cleanup — 20260809

Engine: `nfl-season-engine-v1.24-soft-piles-cleanup`  
Base 100k candidate (before): `nfl-preseason-sim-2026-20260809T163204Z`  
Confirmation bundle (after): `nfl-preseason-sim-2026-20260809T165350Z`  
Source research: `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.23-soft-flags-enterprise-Nteam100000-Nplayer1000-20260809T153419Z`  

## Status

**LOCKED** — official 2026 pre-season baseline (`locked_snapshot: true`).

Lock note: `data/ops/nfl-2026-preseason-baseline-LOCKED-20260809.md`  
Git tag: `nfl-2026-preseason-baseline-v1.24`

## Before → after (pile sizes)

| Soft flag | Before | After |
|-----------|-------:|------:|
| Rush ceiling pile (≥6 near max) | 13 @ ~2623.51 | 1 (max 2714.49) |
| Rush floor pile (≥6 near min) | 11 @ ~1332.58 | 1 (min 1255.89) |
| PF soft-floor pile (≥6 near min) | 11 @ ~286.47 | 2 (min 308.73) |
| Win ceiling pile (≥4 near max) | 9 @ ~13.157 | 1 (max 12.8297) |
| Mike Evans team | SF | TB |

## Conservation / spot checks

| Check | Value |
|-------|------:|
| Pass pool | 125996.4 |
| Rush pool | 64000.0 |
| ARI/BAL/SEA pass | {'ARI': 4350.4, 'BAL': 3578.6, 'SEA': 4258.5} |
| League PF / PA | 11859.2 / 11859.2 |
| Wins Σ / min / max / range | 272.0 / 4.3957 / 12.8297 / 8.434 |
| CIN pass / PF / wins | 5118.9 / 432.89 / 8.8991 |
| JSN rank / yds / team | 3 / 1428.8 / SEA |

## Soft flags remaining

- (none material)

## Gates

| Check | Result |
|-------|--------|
| pass_pool_locked | **PASS** |
| rush_pool_64000 | **PASS** |
| ari_bal_sea_pass_untouched | **PASS** |
| rec_pass_within_1_5pct | **PASS** |
| league_pf_pa_11859 | **PASS** |
| wins_sum_272 | **PASS** |
| win_range_ge_7_5 | **PASS** |
| cin_not_bottom_tier | **PASS** |
| offense_smoke | **PASS** |
| defense_smoke | **PASS** |
| qb_labels_clean | **PASS** |
| jsn_top_tier | **PASS** |
| piles_cleared | **PASS** |
| **ALL** | **PASS** |

## Method
1. Re-finalize 100k research with v1.24 tapered rush stretch (no hard rails) + rush Σ=64k
2. PF/PA: gentler tanh taper + residual micro-spread; volume floors preserved; PF=PA≈11859
3. Wins: softer ceiling taper + point-diff micro-spread; wins Σ=272
4. Mike Evans identity → TB (packaged depth quirk; team pools untouched)
5. Small confirmation = post-board rebuild only (not another 100k MC)
6. **LOCKED** as official 2026 pre-season baseline (user clearance 20260809)
