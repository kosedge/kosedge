# NFL Phase-2 Defense / PF-PA / W-L — Smoke

Date: 2026-08-09  
Engine: `nfl-season-engine-v1.19-defense-points-wl`  
Base offense: locked v1.18 (`nfl-preseason-sim-2026-20260809T095703Z`)  
Web pointer: `nfl-preseason-sim-2026-20260809T100932Z`

## League totals

| Metric | Value |
|--------|------:|
| Points for | 11859.2 |
| Points against | 11859.2 |
| PPG | 21.8 |
| Wins sum | 272.0 |
| Pass yards (locked) | 125998.1 |
| Pass yards allowed | 125998.1 |
| Rush yards allowed | 60000.0 |
| Sacks | 1150.0 |
| INTs forced | 350.27 |

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
| pass_yards_allowed_conserved | **PASS** |
| rush_yards_allowed_conserved | **PASS** |
| **ALL** | **PASS** |

## Top / bottom

- **PF:** top [('SEA', 421.1), ('LA', 415.5), ('DAL', 411.7), ('BUF', 409.4), ('BAL', 406.4)] · bot [('TEN', 333.2), ('CLE', 330.7), ('NYJ', 327.5), ('MIN', 323.4), ('LV', 310.4)]
- **PA:** top [('DAL', 396.7), ('ARI', 393.6), ('WAS', 391.9), ('NYG', 385.8), ('MIA', 385.3)] · bot [('DET', 356.2), ('DEN', 354.5), ('NO', 353.3), ('HOU', 353.1), ('CLE', 348.8)]
- **Wins:** top [('SEA', 10.1), ('BUF', 9.7), ('DEN', 9.65), ('LA', 9.57), ('BAL', 9.56)] · bot [('MIA', 7.31), ('TEN', 7.23), ('NYJ', 7.05), ('ARI', 7.02), ('LV', 6.65)]

Player offense board unchanged. Prior Layer-2 sim wins kept as `sim_expected_wins`.
