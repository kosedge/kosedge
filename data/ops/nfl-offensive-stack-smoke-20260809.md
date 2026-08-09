# NFL Phase-1 Offensive Production Stack — Smoke

Date: 2026-08-09  
Engine: `nfl-season-engine-v1.18-offensive-production-stack`  
Base pass board: locked v1.17 (`nfl-preseason-sim-2026-20260809T092006Z`)  
Web pointer: `nfl-preseason-sim-2026-20260809T095703Z`

## League totals

| Metric | Value | Band |
|--------|------:|------|
| Pass yards | 125998.1 | ~126k locked |
| Rush yards | 60000.0 | 58–62k |
| Receiving yards | 125998.1 | ≈ pass ±1.5% |
| Pass TDs | 1091.0 | 1,050–1,150 |
| Rush TDs | 481.7 | 450–520 |
| Rec TDs | 1091.0 | ≈ pass TDs |
| Offensive TDs | 1572.7 | pass + rush |
| Offensive yards | 185998.1 | pass + rush |
| INTs | 350.3 | — |

## Conservation / criteria

| Check | Result |
|-------|--------|
| pass_rec_yards_within_1_5pct | **PASS** |
| league_pass_tds_band | **PASS** |
| league_rush_tds_band | **PASS** |
| soft_td_ceilings_floors | **PASS** |
| pass_tds_match_rec_tds | **PASS** |
| offensive_yards_identity | **PASS** |
| rush_pool_band | **PASS** |
| pass_pool_locked | **PASS** |
| ari_bal_sea_pass_zones | **PASS** |
| **ALL** | **PASS** |

ARI/BAL/SEA zones: `{'ARI': {'yards': 4082.6, 'ok': True}, 'BAL': {'yards': 3344.6, 'ok': True}, 'SEA': {'yards': 3974.6, 'ok': True}}`

## Top / bottom five

- **Pass yards (QB1):** top Joe Burrow (CIN) 4813.1, Matthew Stafford (LA) 4540.3, Dak Prescott (DAL) 4516.3, Patrick Mahomes (KC) 4376.4, Bo Nix (DEN) 4220.1 · bot Jayden Daniels (WAS) 2951.5, Geno Smith (NYJ) 2990.7, Jalen Hurts (PHI) 3042.2, Deshaun Watson (CLE) 3232.4, Kyler Murray (MIN) 3261.7
- **Pass TDs (QB1):** top Dak Prescott (DAL) 35.8, Joe Burrow (CIN) 35.7, Patrick Mahomes (KC) 35.5, Matthew Stafford (LA) 35.5, Sam Darnold (SEA) 35.5 · bot Geno Smith (NYJ) 27.5, Jayden Daniels (WAS) 28.1, Jalen Hurts (PHI) 28.4, Bryce Young (CAR) 29.0, Deshaun Watson (CLE) 29.1
- **Rush yards (RB):** top James Cook III (BUF) 1186.1, Zach Charbonnet (SEA) 1175.1, Jacory Croskey-Merritt (WAS) 1134.1, Derrick Henry (BAL) 1116.3, D'Andre Swift (CHI) 1104.3 · bot Jeremiyah Love (ARI) 678.8, Ashton Jeanty (LV) 742.5, Chase Brown (CIN) 786.7, Tony Pollard (TEN) 811.3, Jaylen Warren (PIT) 857.4
- **Rush TDs:** top James Cook III (BUF) 9.1, Zach Charbonnet (SEA) 8.9, Derrick Henry (BAL) 8.8, Jacory Croskey-Merritt (WAS) 8.4, Josh Jacobs (GB) 8.2 · bot Jeremiyah Love (ARI) 4.6, Ashton Jeanty (LV) 4.8, Tony Pollard (TEN) 5.4, Aaron Jones Sr. (MIN) 5.7, Chase Brown (CIN) 5.7
- **Rec yards (WR/TE):** top Ja'Marr Chase (CIN) 1062.5, Mike Gesicki (CIN) 1062.5, Colby Parkinson (LA) 1008.9, Puka Nacua (LA) 1008.9, CeeDee Lamb (DAL) 995.5 · bot Chig Okonkwo (WAS) 678.3, Garrett Wilson (NYJ) 692.8, Dallas Goedert (PHI) 711.5, Tetairoa McMillan (CAR) 723.2, Justin Jefferson (MIN) 734.8
- **Rec TDs (WR/TE):** top Rashee Rice (KC) 7.1, Travis Kelce (KC) 7.1, Courtland Sutton (DEN) 7.0, Evan Engram (DEN) 7.0, Mark Andrews (BAL) 6.9 · bot Garrett Wilson (NYJ) 5.4, Tetairoa McMillan (CAR) 5.5, Chig Okonkwo (WAS) 5.6, Brock Bowers (LV) 5.6, Dallas Goedert (PHI) 5.7
- **INTs (QB):** top Joe Burrow (CIN) 13.3, Dak Prescott (DAL) 12.2, Patrick Mahomes (KC) 12.0, Matthew Stafford (LA) 12.0, Jacoby Brissett (ARI) 11.5 · bot Jayden Daniels (WAS) 8.1, Jalen Hurts (PHI) 8.4, Geno Smith (NYJ) 8.8, Drake Maye (NE) 9.1, Lamar Jackson (BAL) 9.2

Team W/L unchanged (272). Stop here for review before Phase 2 (defense).

