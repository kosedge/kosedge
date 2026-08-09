# NFL Defense Variance Lift — Smoke (v1.20)

Date: 2026-08-09  
Engine: `nfl-season-engine-v1.20-defense-variance-lift`  
Base: v1.19 defense on locked v1.18 offense  
Web pointer: `nfl-preseason-sim-2026-20260809T120227Z`

## League totals (conserved)

| Metric | Value |
|--------|------:|
| PA / PF | 11859.2 / 11859.2 |
| Sacks | 1150.0 |
| INTs forced | 350.27 |
| Pass / rush YA | 125998.1 / 60000.0 |
| Wins sum | 272.0 |

## Ranges

| Stat | Min | Max | Spread | Gate |
|------|----:|----:|-------:|------|
| PA | 327.89 | 424.85 | 96.97 | ≥85 |
| Sacks | 25.0 | 47.11 | 22.12 | ≥18 |
| INTs | 6.76 | 14.97 | 8.21 | ≥6 |

## Criteria

| Check | Result |
|-------|--------|
| pf_equals_pa | **PASS** |
| wins_sum_272 | **PASS** |
| league_pf_band | **PASS** |
| pass_yards_still_locked | **PASS** |
| n_teams_32 | **PASS** |
| soft_pf_bands | **PASS** |
| soft_pa_bands | **PASS** |
| sacks_conserved | **PASS** |
| ints_conserved | **PASS** |
| pa_range_ge_85 | **PASS** |
| sack_range_ge_18 | **PASS** |
| int_range_ge_6 | **PASS** |
| pass_yards_allowed_conserved | **PASS** |
| rush_yards_allowed_conserved | **PASS** |
| **ALL** | **PASS** |

## Top / bottom 5

- **PA:** top [('ARI', 424.9), ('CAR', 424.9), ('CIN', 424.9), ('DAL', 424.9), ('GB', 424.9)] · bot [('MIN', 327.9), ('NE', 327.9), ('NO', 327.9), ('PHI', 327.9), ('SEA', 327.9)]
- **Sacks:** top [('CLE', 47.1), ('DEN', 47.1), ('HOU', 47.1), ('JAX', 47.1), ('LA', 47.1)] · bot [('NYG', 25.0), ('NYJ', 25.0), ('SF', 25.0), ('TEN', 25.0), ('WAS', 25.0)]
- **INTs:** top [('ARI', 15.0), ('BAL', 15.0), ('CLE', 15.0), ('DEN', 15.0), ('HOU', 15.0)] · bot [('DET', 6.8), ('MIA', 6.8), ('MIN', 6.8), ('NYJ', 6.8), ('TEN', 6.8)]
- **Wins:** top [('SEA', 10.88), ('BUF', 10.62), ('BAL', 10.56), ('DEN', 10.33), ('DET', 10.26)] · bot [('MIA', 6.31), ('ARI', 6.23), ('TEN', 6.08), ('NYJ', 5.92), ('LV', 5.44)]

## Independent re-verification (handoff factors)

Re-checked 2026-08-09 against handed factors:

- PA: `1 + 0.85 × ((x − 370.6) / 24)` · soft [328, 425]
- Sacks: `1 + 1.4 × ((x − 35.9) / 2.4)` · soft [26, 49]
- INTs: `1 + 1.6 × ((x − 10.95) / 0.65)` · soft [7.0, 15.5]
- Yards: 0.6× PA intensity · renorm to category totals
- Order: stretch → soft clip → exact renorm → Pythagorean wins

Unit test + live `defense_stack_smoke.all_pass` both **PASS**.

**Pre-season snapshot LOCKED** → `nfl-preseason-sim-2026-20260809T120227Z`  
(see `data/ops/nfl-preseason-snapshot-locked.md`).
