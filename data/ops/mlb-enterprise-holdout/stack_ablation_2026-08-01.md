# MLB stack ablation (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds historical densify)  
**Task:** `99bd9535-6354-4722-b0ed-81866683385b` (`run_mlb_stack_ablation`)  
**PR:** [#55](https://github.com/kosedge/kosedge/pull/55) merged → Railway  
**HFA:** 1.025 held constant  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF; props `research_only`  
**Artifact:** `stack_ablation_2026-08-01.json`

## Configs

| ID | Matchup mul | Wind-dir mul | Starter quality | Model version |
|----|:-----------:|:------------:|-----------------|---------------|
| S0 | ON | ON | ERA+WHIP | `mlb-v1-pa-sim-ablate-s0` |
| S1 | OFF | ON | ERA+WHIP | `mlb-v1-pa-sim-ablate-s1` |
| S2 | OFF | OFF | ERA+WHIP | `mlb-v1-pa-sim-ablate-s2` |
| S3 | OFF | ON | K-BB/GB only | `mlb-v1-pa-sim-ablate-s3` |

Each config force-resimmed **628** densify games; leakage stamp repair ON.

## Intersection-n (apples-to-apples)

Fixed set of densify-window games with ML CLV under **all** configs: **n = 476** (≈ prior ~498 closing-line universe).

| Config | ML CLV | RL CLV | Total CLV | ML n |
|--------|-------:|-------:|----------:|-----:|
| S0 | +0.00435 | +0.06329 | +0.00210 | 476 |
| **S1** | **+0.00454** | +0.05063 | +0.00210 | 476 |
| S2 | +0.00393 | **0.00000** | +0.00210 | 476 |
| S3 | +0.00428 | +0.03797 | +0.00210 | 476 |

Notes:
- Densify-window **total CLV is nearly flat** (~+0.002) for all configs — not comparable to full-lookback total CLV (~+0.09 on production), which includes games outside this window.
- S1 beats S0 on intersection ML CLV by **+0.00019** only (noise / not a ship signal).
- S2 **destroys RL CLV** and softens ML — reject wind-dir-off for ML path.
- S3 does not beat S0/S1 on ML CLV.

## Full densify walkforward (ablate model versions)

Ablate versions only contain densify-window projections → walkforward n=512 (vs production ~778 which spans broader lookback).

| Config | Base Brier | Totals MAE | ECE | Leakage |
|--------|-----------:|-----------:|----:|--------:|
| S0 | 0.250234 | 3.4825 | 0.0266 | **0** |
| S1 | 0.250012 | 3.4825 | 0.0239 | **0** |
| **S2** | **0.249566** | **3.4683** | 0.0241 | **0** |
| S3 | 0.250206 | 3.4811 | **0.0238** | **0** |

S2 wins Brier/MAE cosmetics while **losing** ML + RL CLV → do not ship for cosmetics.

## Production reference (unchanged `mlb-v1-pa-sim`)

Post-ablation CLV attribution (lookback 90, not densify-filtered):

| Metric | Value |
|--------|------:|
| avg ML CLV | +0.00490 |
| avg total CLV | +0.08809 |
| avg RL CLV | +0.07856 |
| count | 971 |

Production remains **S0 defaults** (matchup ON, wind-dir ON, ERA+WHIP quality, HFA 1.025).

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** (all configs) |
| Intersection ML CLV | ≥ +0.015 (stretch +0.020) | **FAIL** (best S1 +0.00454) |
| Densify base Brier | ≤ 0.248 | **FAIL** (best S2 0.24957) |
| RL CLV | ≥ +0.08 | **FAIL** on densify intersection (S0 +0.063); prod full-n +0.079 |
| Total CLV | ≥ +0.09 | Densify-window flat; prod full-n +0.088 |

## Decision

**Ship nothing from S1/S2/S3.** Keep production stack = S0 + HFA 1.025.

### Did the “CLV collapse” narrative survive intersection control?

**No — not as a matchup-mul villain story.**

- On the fixed **n=476** densify closing-line set, even **S0 baseline is only ~+0.004 ML CLV**, not ~+0.023.
- Turning matchup off (S1) does **not** restore +0.015/+0.020.
- Therefore the pre-PR48 **+0.023** figure was **sample-composition / universe confounded** (CLV n expanded 498→~1000 after force-resim; densify intersection never shows ~+0.023 under current stack variants).
- Do **not** spend another session chasing matchup nostalgia. Pivot to real talent signal.

### Next lever

1. **SP talent v2** — replace ERA/WHIP with predictive season signals that actually move resolution (K-BB% already trialled as S3 with null result; next = FIP/xFIP / Stuff+ style from Stats API + optional Savant/FG, one knob at a time).
2. **Bullpen role-weighted quality** (closer/setup), not more fatigue knobs.
3. Weather stays **totals track** with park-relative wind later; do not re-enable absolute wind-dir as an ML lever (S2 evidence).

## Anti-ship reminders

- No Odds densify burn.
- Unused holdout stays frozen / stake OFF.
- Props stay `research_only`.
- Do not market-blend to buy Brier 0.24.
