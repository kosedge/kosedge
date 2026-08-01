# MLB late-info stamp / snapshot densify (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `9fbb90f1-d0d1-463d-b8f3-7b0837346c14` (`run_mlb_late_info_stamp_ablation` H0/H1/H2)  
**PR:** [#59](https://github.com/kosedge/kosedge/pull/59)  
**Stack held:** S0 (HFA 1.025, matchup ON, wind-dir ON, era_whip; pitch matchup off; park-rel totals off; timing off)  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Artifact:** `late_info_stamp_2026-08-01.json`

## What was built

1. Snapshot lake `mlb_lineup_sp_snapshots` (JSONL per game_id): `(observed_at, hours_to_pitch, lineup_hash, sp_*, known_*, confirmed)`
2. Live nowcast persists snapshots each cycle
3. Densify accepts `hours_to_first_pitch` stamp (H0=−6h, H1=−3h, H2=−1h) + reconstructs densify snapshots
4. Late-info CLV slice grader (≤3h / ≤6h) — densify reconstruct left **n=0** late-info IDs (context cards lack confirmed/known depth); live lake will populate going forward

## Intersection-n (n = 476)

| Config | ML CLV | RL CLV | Total CLV | WF Brier | MAE | Leak |
|--------|-------:|-------:|----------:|---------:|----:|-----:|
| H0 −6h | **+0.00442** | +0.038 | +0.004 | 0.24977 | 3.485 | **0** |
| H1 −3h | +0.00371 | +0.025 | +0.002 | 0.25034 | 3.486 | **0** |
| H2 −1h | +0.00362 | **0.000** | +0.006 | **0.24933** | **3.483** | **0** |

Late-info slices: **n=0** on densify reconstruct (cannot grade ≤3h/≤6h CLV until live snapshots accumulate).

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** |
| Intersection ML CLV | ≥ +0.010 | **FAIL** (best H0 +0.00442) |
| H2 beats H1 on ML | clear lift | **FAIL** (H2 −0.00009 vs H1; RL → 0) |
| Late-info slice ML | ≥ +0.010 | **FAIL** (n=0) |

## Decision

**Do not change densify stamp default (−3h) or promote late-stamp production behavior.**  
**Keep snapshot lake + nowcast persistence** (measurement infra for live late-info CLV).

H2 softens ML and zeros RL CLV — same anti-pattern as prior timing L1 / S2. Earlier stamp (H0) is slightly best but still noise vs +0.010.
