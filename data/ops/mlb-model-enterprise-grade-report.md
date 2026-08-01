# MLB Model Enterprise Grade Report (2026-08-01)

**Status:** Research / not subscription-worthy for stake marketing  
**Production web branch:** `deploy-vercel`  
**Model service:** `model-service-production-e253.up.railway.app`  
**Model version:** `mlb-v1-pa-sim`  
**Unused holdout (frozen):** 2026-07-18 → 2026-08-10 — train-excluded; stake grade below  
**Odds densify:** not run (credit floor)

## Letter grades (honest)

| Area | Grade | Notes |
|------|:-----:|-------|
| Moneyline sharpness (Brier) | **D+** | Best densify walkforward **0.24896** (HFA off) / **0.2499** (HFA 1.025); gate ≤0.24 fail |
| Moneyline CLV | **D** | +0.023 → ~**+0.006–0.007**; HFA ablation did not recover |
| Calibration (ECE) | **B** | **0.017–0.028** ≪ 0.06 |
| Leakage hygiene | **A** | **11 → 0** via lookback stamp repair |
| Totals MAE | **C+** | ~**3.51–3.52** (gate ~3.5 borderline); total CLV still +0.09 |
| Run-line CLV | **C-** | +0.11 → **+0.05–0.07** under later stacks |
| Props stake | **F / blocked** | `research_only` — unused holdout + props gates not cleared |
| Overall subscription | **D / no-go** | Fail Brier + CLV vs marketing bar; leakage now clean |

## What shipped

| PR | Change | Deploy |
|----|--------|--------|
| [#49](https://github.com/kosedge/kosedge/pull/49) | Ops grade + `force_resim` API | merged → `deploy-vercel` |
| [#50](https://github.com/kosedge/kosedge/pull/50) | HFA→1.025, leakage repair, SP identity, matchup mul, weather wind damp | merged + Railway |
| [#51](https://github.com/kosedge/kosedge/pull/51) | HFA-off trial + 1.025 grade artifacts | merged |
| [#52](https://github.com/kosedge/kosedge/pull/52) | Restore **HFA=1.025** + enterprise report | merged + Railway |
| [#53](https://github.com/kosedge/kosedge/pull/53) | Unused-holdout stake no-go artifacts | merged |

### Engineering detail

1. **HFA ablation** — synthetic + production densify grades; see `hfa_ablation_2026-08-01.md` / `hfa1025_resim_grade_2026-08-01.md`.
2. **Leakage** — root cause: repair only covered densify window; walkforward lookback saw wall-clock stamps. Fix: `_repair_mlb_leakage_stamps` with `LEAST(start−3h, completed_at−1m)` on lookback, run before grade/resim.
3. **SP identity** — live-first Stats API, alias/Jr strip, last-name unique match, expanded priors, season-aware + platoon refresh on historical resim.
4. **Matchup PA** — bounded `_offense_pitcher_matchup_mul` (K/BB vs contact proxy, GB vs elevated recent).
5. **Totals MAE track** — weather reliability 0.72 when temp present but wind missing (no global ML nudge).
6. **Optional ML head** — **skipped**; runs quality already competitive vs ML; CLV regression not a Brier-calibration problem that a market-free head would fix without OOS proof.

## Densify-window metrics (2026-05-20 → 2026-07-17)

| Config | Base Brier | ML CLV | Total CLV | RL CLV | ECE | Leakage | Totals MAE |
|--------|-----------:|-------:|----------:|-------:|----:|--------:|-----------:|
| Pre-HFA subscription | 0.251616 | **+0.0232** | +0.332 | +0.230 | — | 0 | 3.306 |
| HFA 1.035 (PR #48) | 0.250502 | +0.00702 | +0.093 | +0.112 | 0.0277 | **11** | 3.513 |
| HFA **1.025** + ships | **0.249888** | +0.00681 | +0.091 | +0.075 | **0.0167** | **0** | 3.514 |
| HFA 1.0 (off) | **0.248963** | +0.00564 | +0.091 | +0.047 | 0.0223 | **0** | 3.515 |

**Final HFA choice: 1.025** — among leakage-clean candidates, best ML CLV without abandoning Brier/ECE gains. Turning HFA fully off did **not** restore +0.023 CLV (so CLV damage is not HFA-alone; suspect sample/feature stack from PR #48+matchup).

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
2. ML CLV collapsed vs subscription baseline and did not return under HFA ablation.  
3. Unused holdout not large enough / not stake-green.  
4. RL CLV degraded under later stacks — protect before marketing run-line.

## Artifacts

- `data/ops/mlb-enterprise-holdout/hfa_ablation_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/hfa1025_resim_grade_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/unused_holdout_stake_verdict_2026-08-01.md`
- `data/ops/mlb-enterprise-holdout/*_hfa1025_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/*_hfa100_2026-08-01.json`
- `data/ops/mlb-enterprise-holdout/ml_sharpness_resim_grade_2026-08-01.md` (prior)
