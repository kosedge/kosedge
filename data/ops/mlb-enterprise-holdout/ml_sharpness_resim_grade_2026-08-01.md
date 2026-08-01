# MLB moneyline sharpness — force-resim + walkforward grade (2026-08-01)

**Branch / deploy:** `mlb-ml-sharpness` merged as PR #48 → `deploy-vercel` (`51a7cc6e`); ops API patch on `mlb-sharpness-resim-ops` (`66a125b1`).  
**Railway:** `model-service-production-e253.up.railway.app` (brave-art) — health ok / db connected after deploy.  
**Policy:** No Odds API historical densify (credit floor). Unused holdout frozen. Props remain `research_only`.

## Window

| Item | Value |
|------|-------|
| Force-resim dates | **2026-05-20 → 2026-07-17** (established May–Jul densify window) |
| Unused holdout (excluded from train/tune; ungraded for stake) | **2026-07-18 → 2026-08-10** |
| Model | `mlb-v1-pa-sim` |
| Sims / game | 2000 |
| Odds densify | **not run** |

### Resim jobs

| Job | Task ID | Notes |
|-----|---------|-------|
| Force-resim (cap 400) | `48267eef-643a-4ca2-9e7f-1b83796522c0` | `force_resim=true`; deleted 619 prior projections; simulated **400** |
| Fill missing | `b9f9d0af-5d5f-4223-9c5e-da5314c83e2c` | `force_resim=false`; simulated **228** remaining in-window games with outcomes |

**Coverage note:** First force-resim hit `max_games=400` after deleting the full window’s projections — fill pass restored the rest. Prefer `max_games≥1000` on future force-resims.

## Before / after metrics

**Before** = subscription sharpen sprint post-resim (`subscription_sharpen_sprint_report.json`, 2026-07-24) on the same densify window. User reference band: Brier ~0.249–0.252, ML CLV ~+0.023.

| Metric | Before (subscription) | After (full window, final) | Δ |
|--------|----------------------:|---------------------------:|--:|
| Walkforward n | 347 | **778** | +431 |
| Walkforward folds | 11 | 22 | — |
| **Base Brier (ML)** | 0.251616 | **0.250502** | **−0.0011** |
| Calibrated Brier | 0.251601 | 0.251474 | −0.0001 |
| Base MAE totals | 3.306 | 3.5128 | +0.207 |
| Quality / calib Brier | — | 0.250252 | — |
| **ECE** | — | **0.027706** | (gate ≤0.06) |
| CLV n | 498 | 1009 | +511 |
| **ML CLV** | **+0.0232** | **+0.00702** | **−0.0162** |
| Total CLV | +0.33233 | +0.09293 | −0.239 |
| Spread / RL CLV | +0.22967 | +0.1118 | −0.118 |
| Leakage violations | 0 | **11** | +11 |
| Unused holdout excluded from train | true | **true** (195 train skips; 51 eval pts available) | — |
| Props stake | research_only | research_only | — |

### Interim (first 400 games only, before fill)

| Metric | Value |
|--------|------:|
| Base Brier | 0.248886 |
| Calibrated Brier | 0.250304 |
| ML CLV | +0.00822 |
| ECE | 0.015845 |

Resim-embedded holdout after force pass: base Brier **0.246914** (n=425) — not the primary grade (different fold construction / sample).

## Verdict vs 0.24 Brier gate

**Closer, not through.** Full-window walkforward base Brier moved **0.2516 → 0.2505** (still ~105 bps above 0.24). ECE is healthy (0.028 ≪ 0.06).

**CLV regression:** ML / total / RL CLV all fell vs subscription baseline while sample size roughly doubled. Do **not** treat HFA as CLV-neutral in production until this is ablated (window composition vs sharpness). Leakage count 11 needs a timestamp audit (`created_at` vs `completed_at`) before stake marketing.

**Gate status:** fail Brier ≤0.24; unused holdout still frozen / ungraded for stake; props stay research_only.

## Next levers

1. Ablate HFA coefficient (1.035 → 1.02 / 1.025) for Brier vs ML-CLV tradeoff on the densify window only.  
2. Expand SP identity coverage (heuristic-fallback share) + live Statcast / arsenal features.  
3. Fix leakage_violations=11 (projection as-of stamping) before unused-holdout grade.  
4. Grade unused holdout (2026-07-18–08-10) only after train exclusion stays clean — do not stake-market ML until pass.  
5. Avoid market-blend shrink as a first lever.

## Artifacts

- `resim_sharpness_2026-08-01.json` — force-resim result  
- `resim_sharpness_fill_2026-08-01.json` — fill-missing result  
- `walkforward_sharpness_final_2026-08-01.json`  
- `quality_sharpness_final_2026-08-01.json`  
- `clv_sharpness_final_2026-08-01.json`  
- Synthetic wiring check (pre-resim): `ml_sharpness_iteration_2026-08-01.md` (0.2536 → 0.2494)

## Deploy / API notes

- Production model deploy from `deploy-vercel` tip including PR #48 sharpness.  
- Follow-up API patch: `force_resim` / `skip_outcomes_pull` on `POST /api/jobs/mlb-historical-resim`; walkforward `training_days` floor relaxed to 7 for midseason folds.
