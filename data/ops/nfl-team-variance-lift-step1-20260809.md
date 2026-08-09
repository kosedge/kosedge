# NFL Team Variance Lift — Step 1 Smoke

Date: 20260809  
Engine: `nfl-season-engine-v1.21-team-variance-lift`  
Base: v1.20 defense board (`nfl-preseason-sim-2026-20260809T120227Z`)  
Web pointer: `nfl-preseason-sim-2026-20260809T133342Z`  
**Snapshot NOT locked. Step 2 NOT started.**

## Before → After

| Metric | Before | After |
|--------|-------:|------:|
| Wins min / max | 5.44 / 10.88 | 4.12 / 11.70 |
| Wins range | 5.44 | 7.58 |
| Wins Σ | 272.00 | 272.00 |
| League rush yards | 60000 | 64000 |
| PF range | 110.7 | 186.3 |
| League PF / PA | 11859.2 / 11859.2 | 11859.2 / 11859.2 |
| Pass pool | 125998.1 | 125998.1 |

### Top rush teams
- Before: [('BUF', 2304), ('SEA', 2172), ('BAL', 2155), ('CHI', 2145), ('NYG', 2104)]
- After: [('LA', 2542), ('DAL', 2542), ('SEA', 2542), ('SF', 2542), ('CHI', 2542)] (RB@60% ≈ 1525)

### Top receiving teams (≈ locked pass)
- Before: [('CIN', 5119), ('LA', 4861), ('DAL', 4797), ('KC', 4679), ('DEN', 4518)]
- After: [('CIN', 5119), ('LA', 4861), ('DAL', 4797), ('KC', 4679), ('DEN', 4518)] (WR@38% ≈ 1945)

### ARI / BAL / SEA pass (untouched)
{'ARI': 4350.4, 'BAL': 3578.6, 'SEA': 4258.5}

### Wins leaders / trailers
- Top: [('ATL', 11.7), ('BAL', 11.7), ('BUF', 11.7), ('CHI', 11.7), ('DEN', 11.7)]
- Bot: [('ARI', 4.12), ('CAR', 4.12), ('CIN', 4.12), ('LV', 4.12), ('MIA', 4.12)]

## Smoke gates

| Check | Result |
|-------|--------|
| league_pf_pa_11859 | **PASS** |
| wins_sum_272 | **PASS** |
| win_range_ge_7_5 | **PASS** |
| top_rush_supports_1450 | **PASS** |
| top_rec_supports_1500 | **PASS** |
| pass_pool_locked | **PASS** |
| ari_bal_sea_pass_untouched | **PASS** |
| sacks_1150 | **PASS** |
| ints_350 | **PASS** |
| offense_smoke | **PASS** |
| defense_smoke | **PASS** |
| **ALL Step 1** | **PASS** |

## Method
1. Asymmetric rush stretch (pos 1.40× / neg 0.55× about mean, soft 1280–2520) → 64k pool
2. Player rush yards/TDs scaled within team; pass/receiving frozen
3. PF rebuilt from offense → PF residual stretch (0.70) + light PA re-stretch (0.35)
4. Sacks 1150 / INTs ~350 lightly re-stretched with PA; Pythagorean wins → Σ 272

## Conservation
- Pass pool locked (~126k); ARI/BAL/SEA weights unchanged
- League PF = PA = 11859.2
- Sacks = 1150.0; INTs = 350.25
