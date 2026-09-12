# CFB additive raw O/D scoring architecture

**Generated:** `2026-09-12T20:12:18Z`
**Production MATCHUP_RESPONSE:** `1.4` (unchanged)
**LEAGUE_TEAM_PPG:** `25.9` (unchanged)
**Kill switch:** `OFF`  **#532:** DO NOT MERGE
**Lake:** owned Odds-API 2022–24 closes  **Universe:** v1 Layer A QB + prior-year efficiency + league-avg roster

Frozen splits were not touched: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.
2025 sealed. 2026 / W2 n=47 is not in this loss. Actual scores are the objective. Close is diagnostic.
C2 is architectural evidence only. Do not fit the 0.5/0.5 weights.

## Decision

**VARIANCE_COLLAPSE_DO_NOT_PROMOTE**

Ship: **false**. Winner: **none**. Sealed-2025 candidates: **none**.

A1 (and A2, which is identical on this universe) flattened the residual function about as much as C2 did — Val-1 range 21.29 → 9.93, bias −0.09, favorite-agree 0.722. That is the shape we wanted from an additive engine.

It does not survive the distributional gate. Val-1 predicted-total SD is **4.80** against actual SD **16.73** (ratio 0.29). Predicted P90 is 59.4; actual P90 is 77. Predicted >65 frequency is 1.1%; actual is 21.8%. The ≥68 bucket is 4 games. This is variance collapse, not calibration.

Do not write A1, C2, or any α into `priors.py`. Board stays OFF. 2025 stays sealed.

## The equation

`E[pts_i] = pace * (μ + α(Off_i − 50) + β(50 − Def_j)) [* units] + HFA_i + coach_i`

Total: `E[home] + E[away]`  
Spread (existing convention): `E[away] − E[home]`

Scoring level is separated from matchup differential. Both team scores come from one path; total and margin are identities of those scores.

- μ = `25.9` — documented `LEAGUE_TEAM_PPG`. Not a residual intercept.
- center = 50 — documented 0–100 scale. Val-1 means sit near 50.6 / 51.2.
- α = β = `0.190441` (25.9/136) on A1 — each axis owns half a linearized index unit.
- α = β = `0.380882` (25.9/68) on A3 — C3 in point space; negative control.
- Pace scales possessions of the **whole** rate, not a secret product on the mismatch.
- HFA and coaching stay additive point adjustments after the rate is formed.
- 12.6 possessions is the existing E4 scaffold, not a new fit.

No coefficient was searched. No market term. No bucket correction. No spline.

## Why Val-1 ≥68 fell from 54 to 3 — both things are true

E3 predicted ≥68 in **54** Val-1 games. Actual ≥68 happened in **140** Val-1 games.

Those are almost different sets.

| slice | n | E3 pred | C2/A1 pred | actual |
|---|---:|---:|---:|---:|
| E3 predicted ≥68 | 54 | 72.392 | 63.001 | 59.074 |
| actually ≥68 | 140 | 56.857 | 54.744 | 79.221 |

Of E3's 54 predicted-≥68 games, only **15** actually scored 68+. Mean actual on that slice is **59.1**. The ratio was inventing shootouts: 72.4 projected, +13.3 bias. A1 puts those same games at **63.0** — closer to the 59 that happened. That half of the 54→3 drop is *false amplification removed*.

The other half is collapse. 140 games actually went ≥68 (mean 79.2). E3 projected them at 56.9. A1 projected them at **54.7**. C2 at 54.6. A3 (full slope, the tail-restoring control) at 55.8. Nobody in this candidate set can see a real shootout. Prior-year efficiency is pointing at the wrong games.

A5 (C2 with the 7–55 team-score rail off) is **identical** to C2: Val-1 ≥68 n=3. The missing high totals are the half-index slope, not the clamp.

## Better calibration vs variance collapse

Val-1 predicted vs actual totals:

| model | mean | SD | P10 | P50 | P90 | <45 | >65 | >70 | ≥68 n | sd ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **actual** | 53.738 | 16.734 | 34.000 | 52.000 | 77.000 | 31.2% | 21.8% | 15.2% | 140 | 1.000 |
| E3 ratio | 54.870 | 8.795 | 43.750 | 54.350 | 66.410 | 12.0% | 12.6% | 5.6% | 54 | 0.526 |
| C2 additive product | 53.586 | 4.702 | 47.790 | 53.500 | 59.210 | 3.1% | 0.8% | 0.0% | 3 | 0.281 |
| A1 point-space half | 53.644 | 4.796 | 47.790 | 53.520 | 59.430 | 3.1% | 1.1% | 0.0% | 4 | 0.287 |
| A3 point-space full | 53.456 | 9.352 | 41.980 | 53.270 | 64.970 | 16.9% | 10.0% | 4.6% | 49 | 0.559 |

E3 is already under-dispersed (sd ratio 0.53). Its extra spread is almost entirely a false right tail. C2/A1 keep the mean and crush the rest: predicted mass lives in a 48–60 band while a third of football games finish under 45 or over 65.

Calibration inside the actual high-scoring environment (Val-1 actual >65, n=156, mean 77.9):

| model | mean pred on those games | bias |
|---|---:|---:|
| E3 | 56.480 | -21.424 |
| C2 | 54.456 | -23.448 |
| A1 | 54.582 | -23.322 |
| A3 | 55.426 | -22.477 |

And the reverse — games the model called >65:

| model | n | mean pred | mean actual | bias |
|---|---:|---:|---:|---:|
| E3 | 90 | 69.981 | 57.611 | 12.370 |
| C2 | 6 | 67.438 | 53.667 | 13.772 |
| A1 | 8 | 67.433 | 58.750 | 8.683 |
| A3 | 72 | 70.493 | 59.625 | 10.868 |

When the model predicts a shootout, football prints ~54–60. When football prints a shootout, the model prints ~55. That is not a slope we can fix by sliding α between 25.9/136 and 25.9/68.

## Candidate scorecards

Gates were predeclared: Val-1 residual range drop ≥8 vs E3, |bias| ≤3, favorite-agree drop ≤0.03, Train-0/Val-0 ranges also improve, **and** sd(pred)/sd(actual) ≥ 0.50, pred>65 frequency at least 25% of actual, P90 under-spread ≤12, P10 over-spread ≤12. On every split.

| id | Train-0 MAE / bias / range / sd-ratio | Val-0 MAE / bias / range / sd-ratio | Val-1 MAE / bias / range / fav / sd-ratio |
| --- | --- | --- | --- |
| E3_ref | 14.498 / 0.905 / 17.630 / 0.520 | 14.965 / 2.608 / 20.888 / 0.575 | 14.432 / 1.132 / 21.292 / 0.526 / fav=0.725 |
| C2_ref | 13.837 / -0.755 / 6.055 / 0.275 | 13.888 / 0.976 / 9.157 / 0.306 | 13.407 / -0.151 / 10.368 / 0.281 / fav=0.722 |
| A5_c2_unclamped | 13.837 / -0.755 / 6.055 / 0.275 | 13.888 / 0.976 / 9.157 / 0.306 | 13.407 / -0.151 / 10.368 / 0.281 / fav=0.722 |
| A1_point_half | 13.810 / -0.744 / 5.327 / 0.285 | 13.910 / 0.937 / 9.893 / 0.310 | 13.402 / -0.094 / 9.932 / 0.287 / fav=0.722 |
| A2_point_units | 13.810 / -0.744 / 5.327 / 0.285 | 13.910 / 0.937 / 9.893 / 0.310 | 13.402 / -0.094 / 9.932 / 0.287 / fav=0.722 |
| A3_point_full | 14.526 / -0.441 / 19.255 / 0.554 | 15.034 / 1.095 / 23.072 / 0.602 | 14.491 / -0.281 / 22.178 / 0.559 / fav=0.721 |
| A4_point_poss | 13.810 / -0.744 / 5.327 / 0.285 | 13.910 / 0.937 / 9.893 / 0.310 | 13.402 / -0.094 / 9.932 / 0.287 / fav=0.722 |

### Reading the scorecard

- **A1** passes the flatten gate (range 21.29 → 9.93; Train-0 / Val-0 move the same way; fav 0.725 → 0.722). It fails every dispersion check on every split. `VARIANCE_COLLAPSE_DO_NOT_PROMOTE`.
- **A2 equals A1** on this reconstruction. v1 units are league-average, so putting units back on the rate is a no-op. Not evidence that units are harmless on a real-roster path.
- **A4 equals A1** exactly (max |Δ| = `0.000` on 2139 games). The possession rewrite is the same equation. Implementation is consistent.
- **A3** restores dispersion (Val-1 sd ratio 0.56, ≥68 n=49) and **worsens** residual range to 22.18. Same C3 lesson: a pretty mean (−0.28) with a worse shape is subtract-10 in nicer clothes. It also still projects actual >65 games at 55.4.
- **A5 equals C2.** Clamp is not the story.
- Low-projected A1 games still sit about **−6.4** on the <48 bucket. Shape improved. It is not flat.

### Val-1 projected-total buckets and OLS

**E3_ref** range=21.292 OLS slope=0.817 r²=0.157 algebra violations total/margin=0/0 team home bias=-0.169 away bias=1.301 spread MAE close/actual=8.157/14.868

lt_48 n=156 b=-7.974; 48_54 n=194 b=-2.054; 54_60 n=169 b=2.487; 60_68 n=144 b=9.131; ge_68 n=54 b=13.318

**C2_ref** range=10.368 OLS slope=0.670 r²=0.035 algebra violations total/margin=0/0 team home bias=-1.078 away bias=0.927 spread MAE close/actual=8.122/14.615

lt_48 n=77 b=-6.416; 48_54 n=317 b=-1.665; 54_60 n=262 b=2.455; 60_68 n=58 b=3.953; ge_68 n=3 b=13.623

**A5_c2_unclamped** range=10.368 OLS slope=0.670 r²=0.035 algebra violations total/margin=0/0 team home bias=-1.078 away bias=0.927 spread MAE close/actual=8.122/14.615

lt_48 n=77 b=-6.416; 48_54 n=317 b=-1.665; 54_60 n=262 b=2.455; 60_68 n=58 b=3.953; ge_68 n=3 b=13.623

**A1_point_half** range=9.932 OLS slope=0.655 r²=0.034 algebra violations total/margin=0/0 team home bias=-1.044 away bias=0.950 spread MAE close/actual=8.120/14.612

lt_48 n=77 b=-6.416; 48_54 n=316 b=-1.682; 54_60 n=259 b=2.652; 60_68 n=61 b=3.517; ge_68 n=4 b=14.183

**A2_point_units** range=9.932 OLS slope=0.655 r²=0.034 algebra violations total/margin=0/0 team home bias=-1.044 away bias=0.950 spread MAE close/actual=8.120/14.612

lt_48 n=77 b=-6.416; 48_54 n=316 b=-1.682; 54_60 n=259 b=2.652; 60_68 n=61 b=3.517; ge_68 n=4 b=14.183

**A3_point_full** range=22.178 OLS slope=0.808 r²=0.171 algebra violations total/margin=0/0 team home bias=-0.754 away bias=0.473 spread MAE close/actual=7.955/14.746

lt_48 n=195 b=-9.337; 48_54 n=188 b=-2.791; 54_60 n=162 b=2.021; 60_68 n=123 b=9.650; ge_68 n=49 b=12.841

**A4_point_poss** range=9.932 OLS slope=0.655 r²=0.034 algebra violations total/margin=0/0 team home bias=-1.044 away bias=0.950 spread MAE close/actual=8.120/14.612

lt_48 n=77 b=-6.416; 48_54 n=316 b=-1.682; 54_60 n=259 b=2.652; 60_68 n=61 b=3.517; ge_68 n=4 b=14.183

## Distributions by split

Train-0 / Val-0 / Val-1 tell the same story. This is not a 2024 quirk.

### E3_ref

**train_0** sd(pred)/sd(actual)=0.520 P90 gap=8.060 freq>65 ratio=0.625 ≥68 n=71

pred: n=712 mean=55.822 sd=9.169 P5=41.200 P10=43.660 P25=49.100 P50=55.570 P75=62.050 P90=67.940 P95=71.250 <40=3.2% <45=13.2% >60=32.9% >65=16.9% >70=6.5%

actual: n=712 mean=54.917 sd=17.624 P5=27.000 P10=31.000 P25=43.000 P50=55.000 P75=66.000 P90=76.000 P95=83.000 <40=20.4% <45=29.2% >60=37.9% >65=27.0% >70=18.8%

**val_0** sd(pred)/sd(actual)=0.575 P90 gap=5.140 freq>65 ratio=0.765 ≥68 n=90

pred: n=710 mean=55.665 sd=9.840 P5=40.760 P10=42.830 P25=48.240 P50=55.440 P75=62.420 P90=68.860 P95=72.420 <40=3.4% <45=15.2% >60=33.2% >65=18.3% >70=7.3%

actual: n=710 mean=53.058 sd=17.101 P5=24.000 P10=31.000 P25=41.000 P50=53.000 P75=65.000 P90=74.000 P95=82.000 <40=21.0% <45=31.7% >60=33.4% >65=23.9% >70=14.6%

**val_1** sd(pred)/sd(actual)=0.526 P90 gap=10.590 freq>65 ratio=0.577 ≥68 n=54

pred: n=717 mean=54.870 sd=8.795 P5=40.780 P10=43.750 P25=48.760 P50=54.350 P75=60.770 P90=66.410 P95=70.600 <40=4.2% <45=12.0% >60=27.5% >65=12.6% >70=5.6%

actual: n=717 mean=53.738 sd=16.734 P5=30.000 P10=34.000 P25=41.000 P50=52.000 P75=63.000 P90=77.000 P95=84.000 <40=19.7% <45=31.2% >60=31.1% >65=21.8% >70=15.2%

### C2_ref

**train_0** sd(pred)/sd(actual)=0.275 P90 gap=15.660 freq>65 ratio=0.031 ≥68 n=0

pred: n=712 mean=54.162 sd=4.853 P5=46.480 P10=47.610 P25=50.880 P50=54.230 P75=57.690 P90=60.340 P95=62.300 <40=0.3% <45=2.4% >60=11.7% >65=0.8% >70=0.0%

actual: n=712 mean=54.917 sd=17.624 P5=27.000 P10=31.000 P25=43.000 P50=55.000 P75=66.000 P90=76.000 P95=83.000 <40=20.4% <45=29.2% >60=37.9% >65=27.0% >70=18.8%

**val_0** sd(pred)/sd(actual)=0.306 P90 gap=13.260 freq>65 ratio=0.053 ≥68 n=3

pred: n=710 mean=54.034 sd=5.226 P5=45.800 P10=47.330 P25=50.360 P50=54.170 P75=57.520 P90=60.740 P95=62.470 <40=0.1% <45=3.5% >60=13.5% >65=1.3% >70=0.0%

actual: n=710 mean=53.058 sd=17.101 P5=24.000 P10=31.000 P25=41.000 P50=53.000 P75=65.000 P90=74.000 P95=82.000 <40=21.0% <45=31.7% >60=33.4% >65=23.9% >70=14.6%

**val_1** sd(pred)/sd(actual)=0.281 P90 gap=17.790 freq>65 ratio=0.038 ≥68 n=3

pred: n=717 mean=53.586 sd=4.702 P5=46.000 P10=47.790 P25=50.520 P50=53.500 P75=56.800 P90=59.210 P95=61.530 <40=0.4% <45=3.1% >60=8.5% >65=0.8% >70=0.0%

actual: n=717 mean=53.738 sd=16.734 P5=30.000 P10=34.000 P25=41.000 P50=52.000 P75=63.000 P90=77.000 P95=84.000 <40=19.7% <45=31.2% >60=31.1% >65=21.8% >70=15.2%

### A1_point_half

**train_0** sd(pred)/sd(actual)=0.285 P90 gap=15.490 freq>65 ratio=0.047 ≥68 n=0

pred: n=712 mean=54.173 sd=5.029 P5=46.280 P10=47.390 P25=50.830 P50=54.280 P75=57.760 P90=60.510 P95=62.460 <40=0.4% <45=2.8% >60=12.8% >65=1.3% >70=0.0%

actual: n=712 mean=54.917 sd=17.624 P5=27.000 P10=31.000 P25=43.000 P50=55.000 P75=66.000 P90=76.000 P95=83.000 <40=20.4% <45=29.2% >60=37.9% >65=27.0% >70=18.8%

**val_0** sd(pred)/sd(actual)=0.310 P90 gap=13.200 freq>65 ratio=0.053 ≥68 n=3

pred: n=710 mean=53.995 sd=5.302 P5=45.300 P10=47.170 P25=50.320 P50=54.170 P75=57.530 P90=60.800 P95=62.470 <40=0.1% <45=4.2% >60=13.5% >65=1.3% >70=0.0%

actual: n=710 mean=53.058 sd=17.101 P5=24.000 P10=31.000 P25=41.000 P50=53.000 P75=65.000 P90=74.000 P95=82.000 <40=21.0% <45=31.7% >60=33.4% >65=23.9% >70=14.6%

**val_1** sd(pred)/sd(actual)=0.287 P90 gap=17.570 freq>65 ratio=0.051 ≥68 n=4

pred: n=717 mean=53.644 sd=4.796 P5=46.000 P10=47.790 P25=50.520 P50=53.520 P75=56.820 P90=59.430 P95=61.780 <40=0.4% <45=3.1% >60=9.1% >65=1.1% >70=0.0%

actual: n=717 mean=53.738 sd=16.734 P5=30.000 P10=34.000 P25=41.000 P50=52.000 P75=63.000 P90=77.000 P95=84.000 <40=19.7% <45=31.2% >60=31.1% >65=21.8% >70=15.2%

### A3_point_full

**train_0** sd(pred)/sd(actual)=0.554 P90 gap=9.220 freq>65 ratio=0.568 ≥68 n=58

pred: n=712 mean=54.476 sd=9.761 P5=38.930 P10=41.330 P25=48.190 P50=54.750 P75=61.330 P90=66.780 P95=70.540 <40=7.0% <45=17.4% >60=29.1% >65=15.3% >70=5.8%

actual: n=712 mean=54.917 sd=17.624 P5=27.000 P10=31.000 P25=43.000 P50=55.000 P75=66.000 P90=76.000 P95=83.000 <40=20.4% <45=29.2% >60=37.9% >65=27.0% >70=18.8%

**val_0** sd(pred)/sd(actual)=0.602 P90 gap=6.390 freq>65 ratio=0.641 ≥68 n=60

pred: n=710 mean=54.153 sd=10.298 P5=37.230 P10=41.090 P25=47.050 P50=54.650 P75=61.330 P90=67.610 P95=70.670 <40=9.6% <45=20.3% >60=28.7% >65=15.4% >70=5.9%

actual: n=710 mean=53.058 sd=17.101 P5=24.000 P10=31.000 P25=41.000 P50=53.000 P75=65.000 P90=74.000 P95=82.000 <40=21.0% <45=31.7% >60=33.4% >65=23.9% >70=14.6%

**val_1** sd(pred)/sd(actual)=0.559 P90 gap=12.030 freq>65 ratio=0.462 ≥68 n=49

pred: n=717 mean=53.456 sd=9.352 P5=38.720 P10=41.980 P25=47.520 P50=53.270 P75=59.740 P90=64.970 P95=69.520 <40=7.1% <45=16.9% >60=24.0% >65=10.0% >70=4.6%

actual: n=717 mean=53.738 sd=16.734 P5=30.000 P10=34.000 P25=41.000 P50=52.000 P75=63.000 P90=77.000 P95=84.000 <40=19.7% <45=31.2% >60=31.1% >65=21.8% >70=15.2%

## Predeclared candidates (specified before scoring)

### E3_ref (reference)

E3 raw off_eff/def_eff ratio ** 1.00

Lead ratio architecture. Mean bias almost gone; residual range still ~21. The ≥68 bucket is the compression baseline.

### C2_ref (reference)

C2 additive 0.5*off_idx + 0.5*(2−def_idx) (product form)

Architectural evidence only. Do not ship. Do not fit 0.5/0.5. Still a 25.9 × matchup × units × pace product.

### A5_c2_unclamped (diagnostic)

C2 with (7, 55) team-score clamp off

If ≥68 stays near 3 after removing the 55 rail, the missing high totals are the half-index slope, not the clamp.

### A1_point_half (candidate)

μ + (25.9/136)(Off−50) + (25.9/136)(50−Def), pace scales rate

First-principles additive scoring in point space. μ=25.9 is the scoring level. α=β=25.9/136 is each axis owning half a linearized index unit — the C2 slope written without a matchup product. Units off (C1: units were not the slope). Pace scales possessions of the whole rate. No index clamp, no (7, 55) rail, so tails are the equation.

### A2_point_units (candidate)

A1 with unit offense boost × defense dampen on the rate

Same additive rate as A1, then roster units scale the whole rate. Tests whether units belong in an additive engine or reintroduce a product.

### A3_point_full (candidate)

μ + (25.9/68)(Off−50) + (25.9/68)(50−Def) — C3 in point space

Negative control. Full linearized index slope on both axes. C3 already showed a pretty mean and a worse residual range. If A3 looks calibrated only because it stretches tails, it fails.

### A4_point_poss (identity_check)

poss=12.6·pace, ppp = A1 rate / 12.6 (must equal A1)

Possession-explicit rewrite of A1. Algebraically identical if poss=12.6·pace. 12.6 is the existing E4 scaffold, not a fit. If A4 ≠ A1, the implementation is wrong.

## Algebraic consistency

A4 vs A1 max |Δ total| = `0.000` on `2139` paired games. ok=`True`.

Every scored candidate: `away + home = total` and `away − home = spread_home` with zero violations above 0.02. One authoritative scoring path.

## What this means

1. **The ratio was inventing high totals.** E3's 54 predicted-≥68 games scored 59, not 72. Additive form correctly walked those in.
2. **The half-index slope cannot produce football tails.** Predicted SD ~4.8 vs actual ~16.7. That is the 54→3 number.
3. **The full-index slope restores fake tails, not real ones.** A3 looks more dispersed and has a worse residual function. It still projects actual shootouts at 55.
4. **Sliding α is a dead end.** Half-slope = collapse. Full-slope = C3. There is no documented identity between them that we are allowed to fit on Val-1.
5. **Prior-year efficiency does not identify scoring environment.** Sides survive (favorite-agree ~0.72). Totals tails do not. The next honest question is whether *any* v1 feature — or only in-season / game-state information we do not have — can price a 79-point game without reintroducing the ratio.
6. **Nothing here is a production coefficient.** Shape improved. Distribution did not earn sealed-2025 evaluation.

## What this is not

- Not a production change.
- Not permission to write `MATCHUP_RESPONSE = 1.00` or A1/C2 into `priors.py`.
- Not a −10 haircut, bucket correction, isotonic map, or close-anchored spline.
- Not a fit of 0.5/0.5 or of α/β.
- Not permission to open 2025.
- Not a board-on decision.
- Not a winner dressed up as a non-winner. The gate said collapse, and the distributions agree.

