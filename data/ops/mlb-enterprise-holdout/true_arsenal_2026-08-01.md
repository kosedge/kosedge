# MLB true pitch-type arsenal densify (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `b57160a0-1d16-4929-a87d-8074ccb1f7a9` (`run_mlb_pitch_matchup_ablation` M0/M1)  
**PR:** [#60](https://github.com/kosedge/kosedge/pull/60)  
**Stack held:** S0 (HFA 1.025, matchup ON, wind-dir ON, era_whip; timing off; park-rel totals off; stuff off)  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Artifact:** `true_arsenal_2026-08-01.json`

## What was built

True pitch-type arsenal × team batter-family contact (`MLB_PITCH_MATCHUP_ENABLED`, default **off**):

1. **Root-cause fix:** Savant CSV UTF-8 BOM left `pitch_type` empty → prior M1 was stuff-shape-only
2. As-of pitcher mix: FF/SI/FC/SL/CH/CU/FS/ST/KC % + hard/break/soft whiff + hard barrel
3. As-of team batter-family contact/whiff vs hard/break/soft (Statcast `inning_topbot` team join)
4. Interaction mul 0.97–1.03; **stuff-shape fallback OFF** for densify (`pitchmux-m1t`)
5. Indexes shipped in model-service image; Railway `/app` path-safe cache resolver

## Intersection-n (n = 476)

| Config | ML CLV | RL CLV | Total CLV | WF Brier | MAE | Leak |
|--------|-------:|-------:|----------:|---------:|----:|-----:|
| M0 off | +0.00383 | +0.051 | +0.004 | 0.25047 | 3.483 | **0** |
| M1t true arsenal | **+0.00392** | **0.000** | +0.002 | **0.24997** | 3.490 | **0** |

M1t − M0 ML = **+0.00009** (noise). RL CLV collapsed to 0.

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** |
| Intersection ML CLV | ≥ +0.010 | **FAIL** (+0.00392) |
| Stretch | ≥ +0.015 | **FAIL** |
| RL/total not torched | hold | **FAIL** (RL +0.051 → 0) |

## Decision

**Do not flip `MLB_PITCH_MATCHUP_ENABLED`.** Production stays off.  
Wiring + indexes + densify grader remain; true arsenal path is honest but not subscription-grade.

## Live ≤3h companion

See `live_late_info_clv_2026-08-01.md` — lake has 10 live-source games but **late_info_live_n = 0** (needs accumulation).
