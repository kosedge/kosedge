# MLB Model Enterprise Grade Report (2026-08-01)

**Status:** Research / not subscription-worthy for stake marketing  
**Production web branch:** `deploy-vercel`  
**Model service:** `model-service-production-e253.up.railway.app`  
**Model version:** `mlb-v1-pa-sim` (S0 stack: HFA 1.025 + matchup ON + wind-dir ON + ERA/WHIP quality)  
**Unused holdout (frozen):** 2026-07-18 → 2026-08-10 — train-excluded; stake grade below  
**Odds densify:** not run (credit floor)

## Letter grades (honest)

| Area | Grade | Notes |
|------|:-----:|-------|
| Moneyline sharpness (Brier) | **D+** | Densify walkforward ~**0.2496–0.2502**; gate ≤0.24 fail |
| Moneyline CLV | **D** | Intersection densify still **~+0.004** (n=476) after SP FIP/xFIP + BP role trials; prod full-n ~**+0.005**; prior +0.023 was sample-confounded |
| Calibration (ECE) | **B** | **0.017–0.027** ≪ 0.06 |
| Leakage hygiene | **A** | **0** on HFA + stack ablation runs |
| Totals MAE | **C+** | ~**3.47–3.52**; prod full-n total CLV ~+0.088 |
| Run-line CLV | **C-** | Densify intersection **+0.05–0.06** (S0); S2 wind-dir-off → **0** |
| Props stake | **F / blocked** | `research_only` — unused holdout + props gates not cleared |
| Overall subscription | **D / no-go** | Fail Brier + CLV vs marketing bar; leakage clean |

## What shipped

| PR | Change | Deploy |
|----|--------|--------|
| [#49](https://github.com/kosedge/kosedge/pull/49) | Ops grade + `force_resim` API | merged → `deploy-vercel` |
| [#50](https://github.com/kosedge/kosedge/pull/50) | HFA→1.025, leakage repair, SP identity, matchup mul, weather wind damp | merged + Railway |
| [#51](https://github.com/kosedge/kosedge/pull/51) | HFA-off trial + 1.025 grade artifacts | merged |
| [#52](https://github.com/kosedge/kosedge/pull/52) | Restore **HFA=1.025** + enterprise report | merged + Railway |
| [#53](https://github.com/kosedge/kosedge/pull/53) | Unused-holdout stake no-go artifacts | merged |
| [#55](https://github.com/kosedge/kosedge/pull/55) | Stack ablation flags + S0–S3 densify grader | merged + Railway; **no stack ship** |
| [#57](https://github.com/kosedge/kosedge/pull/57) | SP talent v2 (FIP/xFIP) + bullpen role flags + as-of densify | Railway deployed; **no default flip** (T1/T2/B1 fail gates) |

### Engineering detail

1. **HFA ablation** — winner **1.025**; HFA-off worsens CLV.
2. **Leakage** — lookback stamp repair; stays **0**.
3. **SP identity** — live-first Stats API + priors on historical resim; densify now uses **as-of** `byDateRange`.
4. **Matchup PA** — present in prod; **ablation says leave ON** (S1 does not clear +0.015 gate).
5. **Stack ablation (S0–S3)** — see `stack_ablation_2026-08-01.md`. Intersection n=476; matchup-off / wind-dir-off / K-BB-only quality do **not** restore subscription CLV.
6. **SP talent v2 (T0–T2) + bullpen B1** — see `sp_talent_v2_2026-08-01.md`. FIP/xFIP and role-weighted bullpen do **not** clear +0.010 intersection ML CLV; production stays **era_whip** + bullpen quality off.
7. **Optional ML head** — still skipped.

## Densify HFA ladder (prior session)

| Config | Base Brier | ML CLV | Total CLV | RL CLV | ECE | Leakage | Totals MAE |
|--------|-----------:|-------:|----------:|-------:|----:|--------:|-----------:|
| Pre-HFA subscription | 0.251616 | **+0.0232** | +0.332 | +0.230 | — | 0 | 3.306 |
| HFA 1.035 (PR #48) | 0.250502 | +0.00702 | +0.093 | +0.112 | 0.0277 | **11** | 3.513 |
| HFA **1.025** + ships | **0.249888** | +0.00681 | +0.091 | +0.075 | **0.0167** | **0** | 3.514 |
| HFA 1.0 (off) | **0.248963** | +0.00564 | +0.091 | +0.047 | 0.0223 | **0** | 3.515 |

## Stack ablation intersection (2026-08-01) — decision table

Fixed densify closing-line set **n=476** (≈ prior ~498 universe). HFA=1.025 for all.

| Config | Inter ML CLV | Inter RL CLV | Inter Total CLV | WF Brier | MAE | ECE | Leak |
|--------|-------------:|-------------:|----------------:|---------:|----:|----:|-----:|
| S0 baseline | +0.00435 | +0.063 | +0.002 | 0.25023 | 3.483 | 0.027 | 0 |
| S1 matchup OFF | **+0.00454** | +0.051 | +0.002 | 0.25001 | 3.483 | 0.024 | 0 |
| S2 + wind-dir OFF | +0.00393 | **0.000** | +0.002 | **0.24957** | **3.468** | 0.024 | 0 |
| S3 + K-BB quality | +0.00428 | +0.038 | +0.002 | 0.25021 | 3.481 | 0.024 | 0 |

**Ship:** none of S1/S2/S3. Production stays S0.  
**Narrative:** prior +0.023 does **not** appear on intersection even for S0 → treat as sample-composition, not matchup damage. Pivot to deeper SP talent / BP role quality.

Production full-n CLV after ablation (lookback 90): ML **+0.0049**, total **+0.088**, RL **+0.079** (count 971).

## SP talent v2 + bullpen role (2026-08-01) — decision table

Fixed densify closing-line set **n=476**. Stack = S0 (HFA 1.025, matchup ON, wind-dir ON). T0 adds as-of season stats vs prior S0.

| Config | Inter ML CLV | Inter RL CLV | Inter Total CLV | WF Brier | Leak |
|--------|-------------:|-------------:|----------------:|---------:|-----:|
| T0 era_whip (as-of) | +0.00426 | +0.025 | +0.002 | 0.24999 | 0 |
| T1 fip_proxy | +0.00423 | +0.038 | +0.004 | 0.25037 | 0 |
| T2 xfip_proxy | **+0.00434** | +0.038 | +0.002 | 0.25012 | 0 |
| B1 bullpen role | +0.00399 | +0.038 | +0.002 | **0.24946** | 0 |

**Ship:** none. T2’s ML edge over T0 is **+0.00008** (noise). B1 **worsens** ML for a Brier cosmetic. Defaults stay `era_whip` + bullpen role **off**.  
Detail: `sp_talent_v2_2026-08-01.md`.

## Unused-holdout stake verdict

| Item | Result |
|------|--------|
| Train exclusion | Enforced (`unused_holdout_excluded_from_train=true`) |
| Eval resim | 117 games (2026-07-18→08-01), leakage=0 |
| Eval n available (walkforward unused pts) | **51** (≪ 120 target) |
| Stake marketing | **OFF** — fail Brier, fail CLV vs prior bar, holdout n short |
| Props PLAY stake | **OFF** / `research_only` |

Detail: `unused_holdout_stake_verdict_2026-08-01.md`. Do not flip stake flags.

## Blocking subscription-worthiness

1. ML Brier still ≥0.248 vs 0.24 gate.  
2. Intersection ML CLV ~+0.004 ≪ +0.015 gate after stack **and** SP FIP/xFIP / BP role trials; prior +0.023 was confounded.  
3. Unused holdout not large enough / not stake-green.  
4. RL/total CLV must not be softened further for Brier cosmetics (S2 / B1 rejected).

## Artifacts

- `data/ops/mlb-enterprise-holdout/sp_talent_v2_2026-08-01.md` ← **latest talent decision**
- `data/ops/mlb-enterprise-holdout/sp_talent_v2_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/sp_talent_v2_bullpen_b1_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/stack_ablation_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/stack_ablation_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/hfa_ablation_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/hfa1025_resim_grade_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/unused_holdout_stake_verdict_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/*_hfa1025_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/*_hfa100_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/ml_sharpness_resim_grade_2026-08-01.md` (prior)
