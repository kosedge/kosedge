# MLB Model Enterprise Grade Report (2026-08-01)

**Status:** Research / not subscription-worthy for stake marketing  
**Production web branch:** `deploy-vercel`  
**Model service:** `model-service-production-e253.up.railway.app`  
**Model version:** `mlb-v1-pa-sim` (S0 stack: HFA 1.025 + matchup ON + wind-dir ON + ERA/WHIP quality; stuff_proxy **off**; lineup timing **off**; pitch matchup / true arsenal **off**; park-rel totals wind **off**; batter-level arsenal **off**)  
**Unused holdout (frozen):** 2026-07-18 → 2026-08-10 — train-excluded; stake grade below  
**Odds densify:** not run (credit floor)

## Letter grades (honest)

| Area | Grade | Notes |
|------|:-----:|-------|
| Edgeboard ML product | **B+** | Moneyline live on `/edge-board/mlb`; LEAN ≥1.5pp / PLAY ≥3.0pp ([#61](https://github.com/kosedge/kosedge/pull/61)) |
| Moneyline sharpness (Brier) | **D+** | Densify walkforward ~**0.2496–0.2511**; gate ≤0.24 fail |
| Moneyline CLV | **D** | Intersection densify still **~+0.004** (n=476) after FIP/xFIP, BP role, Statcast stuff, lineup timing, late-info stamps, stuff-shape pitch matchup, **true pitch-type arsenal**, and park-rel totals; prod full-n ~**+0.005**; prior +0.023 was sample-confounded |
| Calibration (ECE) | **B** | **0.017–0.027** ≪ 0.06 |
| Leakage hygiene | **A** | **0** on all densify ablation runs this session |
| Totals MAE | **C+** | ~**3.47–3.52**; park-rel wind did not clear MAE |
| Run-line CLV | **C-** | Densify intersection **+0.01–0.06** depending on trial; late −1h stamp → **0**; M1t → **0** |
| Props stake | **F / blocked** | `research_only` — unused holdout + props gates not cleared |
| Overall subscription | **D / no-go** | Fail Brier + CLV vs marketing bar; leakage clean; **Edgeboard UX ≠ model edge** |

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
| [#58](https://github.com/kosedge/kosedge/pull/58) | Statcast `stuff_proxy` (T3) + lineup nowcast wiring + timing L0/L1 | Railway deployed; **no default flip** (T3/L1 fail gates); wiring stays |
| [#59](https://github.com/kosedge/kosedge/pull/59) | Late-info snapshots + pitch matchup + park-rel totals wind | Railway deployed; **no default flip** (H*/M1/W1 fail honest gates); wiring stays |
| [#60](https://github.com/kosedge/kosedge/pull/60) | True pitch-type arsenal + batter-family + live ≤3h lake grader | Railway deployed; **no default flip** (M1t fail; live late-info n=0); wiring stays |
| [#61](https://github.com/kosedge/kosedge/pull/61) | **Edgeboard MLB moneyline** + LEAN/PLAY **1.5pp / 3.0pp** | merged → `deploy-vercel` + Vercel production |

### Engineering detail

1. **HFA ablation** — winner **1.025**; HFA-off worsens CLV.
2. **Leakage** — lookback stamp repair; stays **0**.
3. **SP identity** — live-first Stats API + priors on historical resim; densify now uses **as-of** `byDateRange`.
4. **Matchup PA** — present in prod; **ablation says leave ON** (S1 does not clear +0.015 gate).
5. **Stack ablation (S0–S3)** — see `stack_ablation_2026-08-01.md`. Intersection n=476; matchup-off / wind-dir-off / K-BB-only quality do **not** restore subscription CLV.
6. **SP talent v2 (T0–T2) + bullpen B1** — see `sp_talent_v2_2026-08-01.md`. FIP/xFIP and role-weighted bullpen do **not** clear +0.010 intersection ML CLV; production stays **era_whip** + bullpen quality off.
7. **Statcast stuff (T3) + lineup timing (L0/L1)** — see `statcast_stuff_2026-08-01.md` and `lineup_nowcast_timing_2026-08-01.md`. T3 and L1 both **fail** gates; keep wiring fixes; leave `stuff_proxy` / timing **off**.
8. **Late-info stamps (H0–H2) + pitch matchup (M0/M1) + park-rel totals (W0/W1)** — see decision tables below. All **no-ship** on defaults; snapshot lake + totals-only wind path + pitch-matchup flag remain for live measurement / future trials.
9. **True pitch-type arsenal (M0/M1t) + live ≤3h lake grade** — Prior M1 was BOM-contaminated stuff-shape; true FF/SI/SL/CH/CU mix + **team** batter-family still **no-ship**. Live late-info **n=0**.
10. **Edgeboard moneyline product** — Odds `h2h,totals`; KEIMLB fair ML + `homeWinProb`; ML edge in percentage points; tags LEAN≥1.5 / PLAY≥3.0; O/U remains run-point 1.0/2.5.
11. **Batter-level (lineup ID) contact-by-pitch-type** — wiring in progress (`MLB_PITCH_MATCHUP_BATTER_LEVEL`, default OFF; densify arm `M1b`). **No densify ship decision yet** — do not flip defaults until Inter ML CLV ≥ +0.010.
12. **Optional ML head** — still skipped (likely next architecture path if M1b fails).

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

## SP talent v2 + bullpen role (2026-08-01) — decision table

| Config | Inter ML CLV | Inter RL CLV | Inter Total CLV | WF Brier | Leak |
|--------|-------------:|-------------:|----------------:|---------:|-----:|
| T0 era_whip (as-of) | +0.00426 | +0.025 | +0.002 | 0.24999 | 0 |
| T1 fip_proxy | +0.00423 | +0.038 | +0.004 | 0.25037 | 0 |
| T2 xfip_proxy | **+0.00434** | +0.038 | +0.002 | 0.25012 | 0 |
| B1 bullpen role | +0.00399 | +0.038 | +0.002 | **0.24946** | 0 |

**Ship:** none. Defaults stay `era_whip` + bullpen role **off**.

## Statcast stuff + lineup timing (2026-08-01) — decision table

| Config | Inter ML CLV | Inter RL CLV | Inter Total CLV | WF Brier | Leak |
|--------|-------------:|-------------:|----------------:|---------:|-----:|
| T0 era_whip | **+0.00426** | +0.025 | +0.002 | **0.24999** | 0 |
| T3 stuff_proxy | +0.00414 | +0.051 | +0.002 | 0.25114 | 0 |
| L0 timing off | +0.00413 | +0.013 | +0.002 | **0.24955** | 0 |
| L1 timing sharp | +0.00389 | +0.013 | +0.002 | 0.25042 | 0 |

**Ship:** none of T3 / L1 defaults.

## Late-info stamps + pitch matchup + park-rel totals (2026-08-01) — decision table

Fixed densify closing-line set **n=476**. Stack = S0 unless noted.

| Config | Inter ML CLV | Inter RL CLV | Inter Total CLV | WF Brier | MAE | Leak |
|--------|-------------:|-------------:|----------------:|---------:|----:|-----:|
| H0 stamp −6h | **+0.00442** | +0.038 | +0.004 | 0.24977 | 3.485 | 0 |
| H1 stamp −3h | +0.00371 | +0.025 | +0.002 | 0.25034 | 3.486 | 0 |
| H2 stamp −1h | +0.00362 | **0.000** | +0.006 | **0.24933** | 3.483 | 0 |
| M0 pitch off | +0.00383 | +0.051 | +0.004 | 0.25047 | 3.483 | 0 |
| M1 pitch on | **+0.00444** | **+0.063** | +0.002 | **0.24985** | **3.478** | 0 |
| W0 park-rel off | +0.00386 | +0.025 | +0.002 | **0.24964** | **3.480** | 0 |
| W1 park-rel on | +0.00391 | +0.025 | **+0.004** | 0.25039 | 3.487 | 0 |

**Ship:** none.
- Late-info densify slices **n=0** (reconstructed cards lack confirmed/known depth); live snapshot lake still valuable.
- M1 gains **+0.00061** ML vs M0 — directionally right, far below +0.010.
- W1 total CLV +0.002 but **MAE worse** → human **no-ship** (noise).

Detail: `late_info_stamp_2026-08-01.md`, `pitch_matchup_2026-08-01.md`, `totals_park_wind_2026-08-01.md`.

## True pitch-type arsenal + live ≤3h (2026-08-01) — decision table

Fixed densify closing-line set **n=476**. Stuff-shape fallback **off**. Model suffix `pitchmux-m1t`.

| Config | Inter ML CLV | Inter RL CLV | Inter Total CLV | WF Brier | MAE | Leak |
|--------|-------------:|-------------:|----------------:|---------:|----:|-----:|
| M0 pitch off | +0.00383 | +0.051 | +0.004 | 0.25047 | 3.483 | 0 |
| M1t true arsenal | **+0.00392** | **0.000** | +0.002 | **0.24997** | 3.490 | 0 |

Live ≤3h lake: **638** jsonl / **10** live-source games / **late_info_live_n = 0** → CLV not gradeable.

**Ship:** none. M1t ΔML vs M0 = **+0.00009**; RL torched. Keep `MLB_PITCH_MATCHUP_ENABLED=false`.

Detail: `true_arsenal_2026-08-01.md`, `live_late_info_clv_2026-08-01.md`.

## Batter-level lineup-ID arsenal (2026-08-01) — status

| Item | Status |
|------|--------|
| Flag | `MLB_PITCH_MATCHUP_BATTER_LEVEL` default **false** |
| Densify arm | `M1b` (tasks ablation map) |
| Index | `batter_contact_asof_index.json` (per batter MLBAM id) |
| Densify grade | **Pending** — no metrics yet; **no-ship until graded** |
| Gate | Inter ML CLV ≥ +0.010, RL/total not torched, leak 0 |

If M1b fails: stop PA-mul research; prefer market-aware ML head / architecture change with unused holdout frozen.

## Edgeboard product (2026-08-01)

| Item | Live |
|------|------|
| Markets | `h2h,totals` (not spreads/run line) |
| Labels | Best Moneyline · Best O/U · Our Moneyline · Our O/U |
| ML edge | model − no-vig market (**pp**) |
| Tags | LEAN ≥ **1.5pp** · PLAY ≥ **3.0pp** (totals: run-point 1.0/2.5) |
| PR | [#61](https://github.com/kosedge/kosedge/pull/61) merged |

Full ops narrative: `mlb-enterprise-holdout/mlb_moneyline_status_report_2026-08-01.md`.

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
2. Intersection ML CLV ~+0.004 ≪ +0.010/+0.015 after exhaustive stack / talent / stuff / timing / late-stamp / pitch-matchup / park-wind / **true arsenal** trials; prior +0.023 was confounded.  
3. Unused holdout not large enough / not stake-green.  
4. RL/total must not be softened for cosmetics (S2 / B1 / L1 / H2 / **M1t RL→0** rejected).  
5. Edgeboard showing ML tags correctly does **not** imply provable +EV.

## Next lever

1. **Finish batter-level densify (M1b)** — ship only if ≥ +0.010 Inter ML CLV  
2. If miss: **architecture** (calibrated ML head / market-prior blend) — not another quality mul  
3. **Live ≤3h late-info CLV** when lake has confirms (n=0 today)  
4. Research-grade hold — **do not** open stake marketing

## Artifacts

- `data/ops/mlb-enterprise-holdout/mlb_moneyline_status_report_2026-08-01.md` ← **Full status narrative**
- `data/ops/mlb-enterprise-holdout/true_arsenal_2026-08-01.md` ← True arsenal decision
- `data/ops/mlb-enterprise-holdout/live_late_info_clv_2026-08-01.md` ← Live ≤3h decision
- `data/ops/mlb-enterprise-holdout/true_arsenal_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/live_late_info_clv_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/late_info_stamp_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/pitch_matchup_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/totals_park_wind_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/statcast_stuff_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/lineup_nowcast_timing_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/sp_talent_v2_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/stack_ablation_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/unused_holdout_stake_verdict_2026-08-01.md`
