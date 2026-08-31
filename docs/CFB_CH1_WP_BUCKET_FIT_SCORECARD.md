# CFB Chapter 1 Phase 1 scorecard — bucket map fit

**Map id:** `cfb-bucket-margin-map-v1-20260831`  
**Engine stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31` (power SoT unchanged)  
**Brief:** `docs/CFB_CH1_WP_BUCKET_FIT_BRIEF.md`

## 1A — Replay (required)

| Item                      | Result                                                                                            |
| ------------------------- | ------------------------------------------------------------------------------------------------- |
| HD `/Volumes/KosEdgeData` | **Not mounted** in this VM                                                                        |
| Warehouse                 | Ingested via `ingest_historical_warehouse.py --repo-fallback --skip-pbp --skip-odds` (SDV closes) |
| Discovery                 | `data/ops/cfb-ch1-wp-bucket-corpus.json` — **n_close=3089** (NaN skipped)                         |
| Replay                    | `data/ops/cfb-ch1-replay-2024-2025.json` — live v0.15 hist-proxy vs close                         |

### Bucket N (finite closes, all seasons)

| Bucket  |   n |          P4_vs_P4 | P4_vs_G5 | G5_vs_G5 | FCS |
| ------- | --: | ----------------: | -------: | -------: | --: |
| pick    | 507 | (see corpus JSON) |          |          |     |
| short   | 673 |                   |          |          |     |
| mid     | 693 |                   |          |          |     |
| long    | 429 |                   |          |          |     |
| cupcake | 787 |                   |          |          |     |

### 1A residual (KEI − close) by \|close\| bucket — 2024–2025

| Bucket  |   n |       mean |       MAE |
| ------- | --: | ---------: | --------: |
| pick    | 257 |      −0.91 |      4.41 |
| short   | 357 |      −0.71 |      4.96 |
| mid     | 365 |      −0.16 |  **7.18** |
| long    | 193 |      +3.46 |     11.32 |
| cupcake | 180 | **+10.76** | **17.55** |

Opposite-signed mid vs cupcake pattern holds on hist-proxy (cupcake short of book).

## 1B — Fit

**Train:** 2020–2024 · **Holdout:** 2025  
**Named scales** (`priors.BUCKET_MARGIN_SCALE`):

| Bucket  |     Scale | Why                                                |
| ------- | --------: | -------------------------------------------------- |
| pick    |       1.0 | frozen                                             |
| short   | **1.188** | OLS train, clamped ≤1.25, n≥30                     |
| mid     |       1.0 | frozen — hist OLS wants >1; live TCU needs <1      |
| long    |       1.0 | frozen — OLS>1 would **lengthen** TCU (\|raw\|≈19) |
| cupcake |       1.0 | frozen — raw-bucket n=9 < min_n                    |

`WIN_PROB_MARGIN_SD` stays **15.2**. `USED_IN_SPREAD` tanh **not** enabled.

### Holdout 2025 MAE (model map vs close; before KEI guard)

| Bucket  | Identity MAE |    Fit MAE |          Δ |
| ------- | -----------: | ---------: | ---------: |
| mid     |        7.163 |  **6.920** | **−0.243** |
| cupcake |       17.209 | **17.088** |     −0.121 |
| long    |       10.526 |     10.216 |     −0.310 |
| short   |        4.854 |      5.020 |     +0.166 |

Mid MAE down; cupcake not exploded.

## Canaries

| Canary       | After map                                              | Verdict                                        |
| ------------ | ------------------------------------------------------ | ---------------------------------------------- |
| Top-7 power  | OSU ORE MISS MIA IU TAMU ND                            | **Pass**                                       |
| BALL@OSU KEI | **−42.2**, WP **0.98**                                 | **Pass** (cupcake identity)                    |
| UNC@TCU KEI  | **−20.39** (raw long bucket, scale 1.0)                | **Blocker** — residual vs −7.5 still **12.89** |
| HAW@STAN KEI | **+10.90** (wrong side)                                | **Chapter 2 blocker** — flip not required      |
| USF E[wins]  | mean **8.38** vs OSU **9.54**; USF std 1.12 < OSU 1.31 | **Pass**                                       |
| Utah natty   | **6.2%**                                               | Untouched                                      |

## Blockers

1. **TCU / mid-band live residual** — Honest hist-proxy train cannot compress live long raw margins without worsening holdout or inventing a team branch. Map is **not** the lever for TCU −20 → −7.5.
2. **Hawaii polarity** — Compose / expected-points side wrong; monotonic map cannot flip. Park for **Chapter 2** (power units), not a failed merge.
3. **Lake closes** — This run used SDV fill only (`--skip-odds`). Re-run 1A on HD with odds lake when available for denser closes (inventory 4,994).

## Done / Fail check

| Criterion                         | Status      |
| --------------------------------- | ----------- |
| Honest map + holdout mid MAE down | **Done**    |
| Canaries explained                | **Done**    |
| Hawaii parked for Ch2             | **Done**    |
| TCU −8.5 via SD or `if`           | **Avoided** |
| Top-7 shuffle                     | **Avoided** |
| Cupcake WP back in 80s            | **Avoided** |
| USF cloned to OSU                 | **Avoided** |
