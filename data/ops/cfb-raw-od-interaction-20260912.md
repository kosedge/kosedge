# CFB raw O/D interaction specification

**Generated:** `2026-09-12T18:46:16Z`  
**Production MATCHUP_RESPONSE:** `1.40` (unchanged)  
**Kill switch:** `OFF`  
**#532:** DO NOT MERGE  
**Lake:** owned Odds-API 2022–24 closes  
**Universe:** v1 Layer A QB + prior-year efficiency + league-avg roster  

Frozen splits were not touched: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.  
2025 sealed. 2026 / W2 n=47 is not in this loss. Actual scores are the objective. Close is diagnostic.

---

## Decision

**SHAPE_IMPROVED_DO_NOT_SHIP**

Ship: **false**. Winner: **none**.

C2 (additive raw O/D) is the only predeclared identity that passed the flatten gate. That is research evidence about *form*, not a production coefficient.

Do not write `MATCHUP_RESPONSE = 1.00`. Do not write C2 into `priors.py`. Board stays OFF.

---

## Why E3 is still sloped

Val-1 E3 (n=717): mean residual **+1.13**, MAE **14.43**, favorite-agree **0.725**. Gorgeous mean. Ugly shape.

| projected total | n | bias vs actual | mean model | mean actual |
|---|---:|---:|---:|---:|
| <48 | 156 | **−7.97** | 45.1 | 53.1 |
| 48–54 | 194 | −2.05 | 51.0 | 53.1 |
| 54–60 | 169 | +2.49 | 57.0 | 54.5 |
| 60–68 | 144 | +9.13 | 63.3 | 54.2 |
| ≥68 | 54 | **+13.32** | 72.4 | 59.1 |

Bucket range **21.29**. OLS `residual ~ projected total`: slope **0.82**, r² **0.16**.

### It is not the baseline

Val-1 raw scale is centered: mean off_eff **50.64**, mean def_eff **51.19**, mean raw ratio **1.028**. `2 × 25.9 = 51.8` vs mean actual **53.74**. That is a ~2-point intercept, not a 21-point slope.

Composed indexes are still drunk (mean off_idx **1.14-ish** vs def **1.01**, gap **+0.12**), but E3 does not use those indexes in the ratio. The leftover compose gap is a red herring for this slope.

### It is not leftover pace / units

C1 forces units=1 and pace=1. Val-1 range **21.29 → 20.49**. Bias **+1.13 → +1.11**. Favorite-agree unchanged. Explosiveness leaking through pace is not the shape.

### It is the multiplicative map

O/D interaction on E3 Val-1:

| offense × facing defense | n | bias | mean model |
|---|---:|---:|---:|
| off_hi × def_lo | 25 | **+14.01** | 70.7 |
| off_lo × def_hi | 29 | **−9.98** | 39.9 |
| off_hi × def_hi | 133 | +5.39 | 54.7 |
| off_lo × def_lo | 135 | +0.27 | 54.5 |
| off_mid × def_mid | 83 | −1.74 | 54.3 |

The product `eff_idx(off) / eff_idx(def)` lifts both sides when an efficient offense meets a porous defense, and crushes both when the reverse happens. Same-quality games (hi/hi, lo/lo) sit near the mean. That is exactly a slope against projected total: the model’s high totals *are* the off_hi/def_lo games.

Clamping is not the story (per-team 55-pt cap is rare on E3). Shared HFA is intercept. The transformation from raw efficiency **ratio** into points is the slope.

---

## Predeclared candidates (specified before scoring)

| id | Identity | Rationale |
|---|---|---|
| E3 | `25.9 × (off_idx / def_idx)` | Lead architecture. Mean fixed, shape not. |
| C1 | E3 with units=1, pace=1 | Is leftover compose the slope? |
| C2 | `25.9 × (0.5·off_idx + 0.5·(2−def_idx))` | Offense and opponent defense add. No product. |
| C3 | `25.9 × (1 + (off_eff−def_eff)/68)` | First-order Taylor in the raw 0–100 scale. |
| C4 | `25.9 × (1 + tanh(ratio−1))` | Predeclared saturation. Not a fitted spline. |

50/50 weights on C2 and the `/68` on C3 are the existing index identity, not a Train-0 fit. tanh has no free k.

Flatten gate (also predeclared): Val-1 bucket-bias range drops ≥8 vs E3, |mean bias| ≤3, favorite-agree drop ≤0.03, and Train-0 / Val-0 ranges also improve.

---

## Results

| id | Train-0 MAE / bias / range | Val-0 MAE / bias / range | Val-1 MAE / bias / range / fav | Val-1 spread MAE vs close |
|---|---|---|---|---|
| E3 | 14.50 / +0.91 / 17.63 | 14.97 / +2.61 / 20.89 | 14.43 / +1.13 / **21.29** / 0.725 | 8.16 |
| C1 no leak | 14.44 / +0.84 / 15.93 | 14.88 / +2.56 / 20.77 | 14.36 / +1.11 / 20.49 / 0.725 | 8.15 |
| **C2 additive** | **13.84 / −0.76 / 6.06** | **13.89 / +0.98 / 9.16** | **13.41 / −0.15 / 10.37 / 0.722** | 8.12 |
| C3 raw diff | 14.52 / −0.44 / 19.18 | 15.03 / +1.11 / 23.04 | 14.47 / −0.26 / 22.13 / 0.721 | — |
| C4 tanh | 14.39 / +0.75 / 17.83 | 14.86 / +2.47 / 21.22 | 14.35 / +1.04 / 19.91 / 0.726 | — |

C1 / C3 / C4 fail the flatten gate. C3 is the instructive miss: it fixes the *mean* (Val-1 −0.26) and **worsens** the range. A pretty intercept with a worse slope is the exact failure mode we refused when someone wanted to subtract 10.

C4 barely moves. `tanh` is not enough squash once the ratio is already 1.3–1.8.

### C2 Val-1 projected-total buckets

| projected | n | bias | mean model | mean actual |
|---|---:|---:|---:|---:|
| <48 | 77 | −6.42 | 45.5 | 51.9 |
| 48–54 | 317 | −1.66 | 51.4 | 53.0 |
| 54–60 | 262 | +2.45 | 56.6 | 54.1 |
| 60–68 | 58 | +3.95 | 62.1 | 58.1 |
| ≥68 | 3 | +13.62 | 68.6 | 55.0 |

Range used in the gate is **10.37** (buckets with n≥15). The ≥68 bin almost disappeared (54 → 3). OLS slope 0.67 but r² **0.03** — the prediction-error link is much weaker.

Favorite-agree 0.725 → 0.722. Spread MAE vs close 8.16 → 8.12. Sides did not collapse the way identity matchup did (that went to 0.616).

Year stability: C2 range is 6.06 / 9.16 / 10.37 across 2022 / 2023 / 2024. Same direction every year.

---

## What this means

1. **E3’s remaining slope is the ratio.** Not the 25.9 baseline, not HFA, not pace, not a vintage join.
2. **Additive raw O/D is the first identity that flattens the conditional error without throwing away sides.** Product → sum is the architectural move.
3. **C2 is not flat.** Low-projected games still sit about −6. A 10-point range is better than 21. It is not calibration.
4. **C3 proves a mean-only win is worthless.** Do not ship a difference model just because bias is −0.26.
5. **Nothing here is a coefficient search.** The 0.5/0.5 on C2 was predeclared. If someone now “fits” those weights on Train-0, they are starting a different, later phase.

---

## What this is not

- Not a production change.
- Not permission to write `MATCHUP_RESPONSE = 1.00`.
- Not a −10 haircut, bucket correction, isotonic map, or close-anchored spline.
- Not a board-on decision.
- Not a winner. C2 passed a flatten *gate*. It did not earn `priors.py`.

Next design work, if any: specify an additive raw O/D scoring equation (possessions × finishing can come after the interaction form is honest), and score that spec on these same splits. Until a residual function is actually flat out of sample, CFB stays dark.
