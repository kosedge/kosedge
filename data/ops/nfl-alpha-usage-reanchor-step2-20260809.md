# NFL Alpha Usage Re-anchor — Step 2 Smoke

Date: 20260809  
Engine: `nfl-season-engine-v1.22-alpha-usage-reanchor`  
Base: Step 1 board (`nfl-preseason-sim-2026-20260809T133342Z`)  
Web pointer: `nfl-preseason-sim-2026-20260809T141337Z`  
**Snapshot NOT locked. Step 3 NOT started. Awaiting user review.**

## JSN

| | Before | After |
|--|-------:|------:|
| WR rank | 8 | 3 |
| Rec yards | 892 | 1575 |

## Top WRs

| Rank | Player | Team | Rec yds | Before |
|-----:|--------|------|--------:|-------:|
| 1 | Puka Nacua | LA | 1615 | 1009 |
| 2 | Ja'Marr Chase | CIN | 1606 | 1062 |
| 3 | Jaxon Smith-Njigba | SEA | 1575 | 892 |
| 4 | Amon-Ra St. Brown | DET | 1504 | 914 |
| 5 | Justin Jefferson | MIN | 1381 | 735 |
| 6 | George Pickens | DAL | 1380 | 634 |
| 7 | Rashee Rice | KC | 1365 | 992 |
| 8 | CeeDee Lamb | DAL | 1324 | 996 |
| 9 | Courtland Sutton | DEN | 1318 | 977 |
| 10 | Chris Olave | NO | 1279 | 864 |
| 11 | Garrett Wilson | NYJ | 1261 | 693 |
| 12 | Zay Flowers | BAL | 1231 | 764 |

## Top RBs

| Rank | Player | Team | Rush yds | Before |
|-----:|--------|------|---------:|-------:|
| 1 | Kyren Williams | LA | 1432 | 1311 |
| 2 | Javonte Williams | DAL | 1432 | 1309 |
| 3 | Zach Charbonnet | SEA | 1432 | 1376 |
| 4 | James Cook III | BUF | 1432 | 1309 |
| 5 | Jacory Croskey-Merritt | WAS | 1432 | 1390 |
| 6 | Bhayshul Tuten | JAX | 1432 | 1309 |
| 7 | Bucky Irving | TB | 1432 | 1309 |
| 8 | Josh Jacobs | GB | 1432 | 1309 |
| 9 | Cam Skattebo | NYG | 1432 | 1309 |
| 10 | Bijan Robinson | ATL | 1432 | 1317 |
| 11 | Rhamondre Stevenson | NE | 1432 | 1317 |
| 12 | Christian McCaffrey | SF | 1432 | 1357 |

## Conservation

| Check | Value |
|-------|------:|
| max \|rec−pass\| / pass | 0.0000% |
| rush team sums conserved | True |
| pass pool | 125998.1 |
| rush pool | 64000.0 |
| ARI/BAL/SEA pass | {'ARI': 4350.4, 'BAL': 3578.6, 'SEA': 4258.5} |

## Team win / PF picture (unchanged from Step 1)

| Metric | Value |
|--------|------:|
| Wins min / max | 4.12 / 11.70 |
| Wins range | 7.58 |
| Wins Σ | 272.00 |
| League PF / PA | 11859.2 / 11859.3 |

## Smoke gates

| Check | Result |
|-------|--------|
| top_wr_multiple_1400 | **PASS** |
| top_wr_end_1550 | **PASS** |
| top_rb_1400 | **PASS** |
| jsn_top_tier | **PASS** |
| rec_pass_within_1_5pct | **PASS** |
| rush_sum_conserved | **PASS** |
| pass_pool_locked | **PASS** |
| ari_bal_sea_pass_untouched | **PASS** |
| league_pf_pa_11859 | **PASS** |
| wins_sum_272 | **PASS** |
| win_range_ge_7_5 | **PASS** |
| offense_smoke | **PASS** |
| step1_gates_held | **PASS** |
| **ALL Step 2** | **PASS** |

## Method
1. Hierarchical usage fallback (WR1 ≫ TE1) replaces WR=TE logjam
2. 2025 elite priors: sticky share = max(prior_tgt×0.875, prior_yards×retention/team_pool)
3. Alpha volume regression cut to 8% (efficiency regression unchanged)
4. Yard floors: top-5 WR ≥1400; WR12–15 band ≥1150; bell-cow RB ≥1400 when team rush supports
5. TE compressed when sticky WR1 alpha present; rookies/depth not inflated
6. Team pass/rush locked; conservation renorm; team W/L+PF carried forward

## Status
**NOT locked** — awaiting user review before Step 3 final lock.
