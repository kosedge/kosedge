# MLB pitch-level matchup densify (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `8092800b-971a-4381-9fb3-a3b6c6750ec0` (`run_mlb_pitch_matchup_ablation` M0/M1)  
**PR:** [#59](https://github.com/kosedge/kosedge/pull/59)  
**Stack held:** S0 (HFA 1.025, matchup ON, wind-dir ON, era_whip; timing off; park-rel totals off)  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Artifact:** `pitch_matchup_2026-08-01.json`

## What was built

Pitch-type / arsenal PA-shape mul (`MLB_PITCH_MATCHUP_ENABLED`, default **off**):

- Distinct from season `matchup_mul` (K/BB/GB) and from `stuff_proxy` starter_quality rewrite
- As-of arsenal index (pitch families) with **stuff-shape fallback** when pitch-type CSV absent
- Interacts pitcher break-whiff / hard-barrel with offense contact/power proxies
- Bounded 0.97–1.03; densify writes `{base}-pitchmux-mN`

## Intersection-n (n = 476)

| Config | ML CLV | RL CLV | Total CLV | WF Brier | MAE | Leak |
|--------|-------:|-------:|----------:|---------:|----:|-----:|
| M0 off | +0.00383 | +0.051 | +0.004 | 0.25047 | 3.483 | **0** |
| M1 on | **+0.00444** | **+0.063** | +0.002 | **0.24985** | **3.478** | **0** |

M1 − M0 ML = **+0.00061** (directionally right; far below gate).

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** |
| Intersection ML CLV | ≥ +0.010 | **FAIL** (+0.00444) |
| Stretch | ≥ +0.015 | **FAIL** |
| RL/total not torched | hold | **PASS** (RL up; total flat/soft) |

## Decision

**Do not flip `MLB_PITCH_MATCHUP_ENABLED`.** Production stays off.  
Wiring + densify grader remain for a future true pitch-type arsenal index (not stuff-shape fallback alone).
