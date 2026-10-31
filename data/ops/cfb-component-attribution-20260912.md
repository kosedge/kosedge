# CFB broader recalibration — component attribution

**Generated:** `2026-09-12T04:00:57Z`  
**Contract:** `cfb-qb-feature-v1`  
**Production MATCHUP_RESPONSE:** `1.4` (unchanged)  
**Production LEAGUE_TEAM_PPG:** `25.9` (unchanged)  
**Authorized floor (not a coefficient):** `0.7`  
**Objective:** actual MAE / bias / tail. Close is diagnostic only.  
**Kill switch:** ON. 2025 sealed. 2026 excluded. No PLAY. No Line Curve.

## Decision

**MULTIVARIATE RECALIBRATION**

- Val-1 frozen 1.40 MAE=16.651408647140865 bias=10.10044630404463 tail_n=217
- Val-1 authorized 0.70 floor MAE=13.98700139470014 bias=4.6185774058577405 tail_n=5 |m-c|=7.370432357043236
- 2*LEAGUE_TEAM_PPG=51.8 vs mean actual 53.73779637377964 (PPG-only gap -1.94)
- mean(offense_index)−mean(defense_index)=+0.1249
- error type @1.40: MULTIPLE ['LOCATION', 'SCALE', 'NONLINEARITY']
- largest one-family move: multiplicative_matchup |Δbias@1.40|=10.007 |Δbias@0.70|=4.526
- More than one family moves Val-1 location/MAE by a material amount. A single-knob fit would re-create the 1.40 compensating-knob problem.

Evidence required to open parameters: ≥3 material families, or centering AND QB both ≥1.0 bias-move @1.40, or matchup identity AND remaining centering @0.70. Fit jointly on Train-0 with Val-0/Val-1 holdout. Still no 2025.

Do not:

- Do not sweep MATCHUP_RESPONSE below 0.70.
- Do not write production constants.
- Do not unseal 2025 or use 2026.
- Do not open PLAY or Line Curve.

## Ranked root-cause attribution

| rank | family | \|Δbias\| @1.40 | \|Δbias\| @0.70 | MAE improve @1.40 | tail n drop @1.40 |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | multiplicative_matchup | 10.007 | 4.526 | 3.392 | 217.0 |
| 2 | qb_talent_scale | 9.453 | 4.445 | 3.001 | 202.0 |
| 3 | od_strength_centering | 9.349 | 4.440 | 2.938 | 192.0 |
| 4 | double_counted_strength | 5.055 | 2.231 | 2.411 | 182.0 |
| 5 | home_field | 1.958 | 1.958 | 0.896 | 53.0 |
| 6 | efficiency_level | 0.566 | 0.045 | 0.607 | 171.0 |
| 7 | nonlinear_exponent | 0.534 | 0.211 | 0.314 | 17.0 |
| 8 | clipping | 0.081 | 0.030 | -0.038 | -2.0 |
| 9 | pace_possessions | 0.016 | 0.001 | 0.048 | -1.0 |
| 10 | supporting_cast | 0.000 | 0.000 | -0.000 | -0.0 |

Error type @ frozen 1.40: **MULTIPLE** `['LOCATION', 'SCALE', 'NONLINEARITY']`

## Train-0 / Val-0 / Val-1 confirmation (top families)

Identity matchup, QB neutralization, and O/D centering are the same causal chain: Layer A talent ~69–71 → mean QB index 1.23 → mean offense index 1.14 vs defense 1.01 → mean ratio 1.13 → `ratio**r` lifts both sides. Turning any one of those three off collapses location. Identity matchup also collapses prediction std to ~0.57 — a location diagnostic, not a shippable model.

### Panel A vs frozen 1.40

| family | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / bias |
| --- | --- | --- | --- |
| frozen_140 | 712 / 17.471 / 11.888 | 710 / 17.793 / 12.327 | 717 / 16.651 / 10.100 |
| qb_talent_scale | 712 / 13.900 / 0.195 | 710 / 14.174 / 1.784 | 717 / 13.650 / 0.647 |
| od_strength_centering | 712 / 14.035 / 0.330 | 710 / 14.238 / 1.821 | 717 / 13.713 / 0.751 |
| multiplicative_matchup | 712 / 14.116 / -1.047 | 710 / 13.744 / 0.779 | 717 / 13.260 / 0.093 |
| double_counted_strength | 712 / 14.544 / 5.494 | 710 / 14.937 / 6.574 | 717 / 14.241 / 5.046 |
| home_field | 712 / 16.509 / 9.938 | 710 / 16.923 / 10.379 | 717 / 15.755 / 8.143 |

### Panel B vs authorized 0.70 remaining-error reference

| family | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / bias |
| --- | --- | --- | --- |
| floor_070 | 712 / 14.380 / 4.791 | 710 / 14.566 / 6.022 | 717 / 13.987 / 4.619 |
| qb_talent_scale | 712 / 13.777 / -0.642 | 710 / 13.758 / 1.085 | 717 / 13.218 / 0.174 |
| od_strength_centering | 712 / 13.810 / -0.624 | 710 / 13.735 / 1.069 | 717 / 13.207 / 0.179 |
| multiplicative_matchup | 712 / 14.116 / -1.047 | 710 / 13.744 / 0.779 | 717 / 13.260 / 0.093 |
| double_counted_strength | 712 / 13.944 / 1.986 | 710 / 13.950 / 3.479 | 717 / 13.418 / 2.387 |
| home_field | 712 / 14.041 / 2.841 | 710 / 14.125 / 4.074 | 717 / 13.467 / 2.661 |

## Complete totals equation

```
qb_index = clamp((1+(talent-50)/80) * class_mult * cast_mult)
offense_score = 0.34*off_eff + 0.22*roster + 0.24*qb_score + 0.10*skill + 0.10*ol
defense_score = 0.36*def_eff + 0.12*roster + 0.24*F7 + 0.20*secondary + 0.08*exp
index = clamp(1 + (score-50)/68)  then multiplicative post-compose blends
ratio = soft_clamp(off / max(0.50, opp_def), 0.52, 1.45, retain=0.42)
pts = clamp(25.9 * ratio**r * boost * dampen * pace + HFA + coach, 7, 55)
total = home_pts + away_pts + ST_nudge
```

Terms that can move the predicted total:

- LEAGUE_TEAM_PPG (baseline, multiplicative)
- offense_index / defense_index (ratio)
- MATCHUP_RESPONSE and W1–W4 soften (exponent)
- ratio soft-clamp + excess retain
- unit offense boost / defense dampen (identity on v1)
- pace / explosiveness
- variable HFA (additive to home, therefore to total)
- coaching week adj (identity on v1)
- EXPECTED_POINTS_CLAMP per team
- special-teams nudge (identity on v1)
- QB talent / class / cast (via compose + QB_INDEX_BLEND)
- efficiency off/def (via weighted score + EFF_*_BLEND)
- post-compose double application of QB/efficiency/units

If E[offense_index] > E[defense_index], then E[ratio] > 1 on both sides of a typical game. ratio**1.40 is convex for ratio>1, so the upper tail explodes and both team scores rise. Lowering r shrinks that convexity but cannot fix a systematic O>D location or a double-counted QB/efficiency lever.

## Panel A — one family vs frozen 1.40

Actual-primary. Negative ΔMAE / Δbias is an improvement versus 1.40.

| family | Val-1 n | MAE | bias | RMSE | mean model | std model | |m−c| | tail n | tail bias | ΔMAE vs ref | Δbias vs ref |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frozen_140 | 717 | 16.651 | 10.100 | 20.429 | 63.838 | 8.212 | 12.177 | 217 | 17.906 | 0.000 | 0.000 |
| od_strength_centering | 717 | 13.713 | 0.751 | 17.398 | 54.489 | 7.051 | 6.425 | 25 | 12.369 | -2.938 | -9.349 |
| multiplicative_matchup | 717 | 13.260 | 0.093 | 16.802 | 53.831 | 0.572 | 5.599 | 0 | — | -3.392 | -10.007 |
| qb_talent_scale | 717 | 13.650 | 0.647 | 17.219 | 54.385 | 6.150 | 6.181 | 15 | 8.925 | -3.001 | -9.453 |
| supporting_cast | 717 | 16.651 | 10.100 | 20.429 | 63.838 | 8.212 | 12.177 | 217 | 17.906 | 0.000 | 0.000 |
| pace_possessions | 717 | 16.603 | 10.084 | 20.349 | 63.822 | 7.962 | 12.124 | 218 | 17.568 | -0.048 | -0.016 |
| home_field | 717 | 15.755 | 8.143 | 19.481 | 61.881 | 8.250 | 10.650 | 164 | 17.569 | -0.896 | -1.958 |
| clipping | 717 | 16.689 | 10.182 | 20.482 | 63.920 | 8.356 | 12.258 | 219 | 18.110 | 0.038 | 0.081 |
| double_counted_strength | 717 | 14.241 | 5.046 | 17.688 | 58.784 | 5.432 | 7.849 | 35 | 14.147 | -2.411 | -5.055 |
| nonlinear_exponent | 717 | 16.337 | 9.567 | 20.051 | 63.305 | 7.844 | 11.686 | 200 | 17.177 | -0.314 | -0.534 |
| efficiency_level | 717 | 16.044 | 9.535 | 19.427 | 63.272 | 3.453 | 11.293 | 46 | 17.023 | -0.607 | -0.566 |

## Panel B — one family vs authorized 0.70 remaining-error reference

0.70 is **not** an earned coefficient. This panel attributes the leftover +4–5 bias.

| family | Val-1 n | MAE | bias | RMSE | mean model | std model | |m−c| | tail n | tail bias | ΔMAE vs ref | Δbias vs ref |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| floor_070 | 717 | 13.987 | 4.619 | 17.387 | 58.356 | 3.888 | 7.370 | 5 | 12.584 | 0.000 | 0.000 |
| od_strength_centering | 717 | 13.207 | 0.179 | 16.734 | 53.917 | 3.617 | 5.346 | 0 | — | -0.780 | -4.440 |
| multiplicative_matchup | 717 | 13.260 | 0.093 | 16.802 | 53.831 | 0.572 | 5.599 | 0 | — | -0.727 | -4.526 |
| qb_talent_scale | 717 | 13.218 | 0.174 | 16.742 | 53.911 | 3.169 | 5.397 | 0 | — | -0.769 | -4.445 |
| supporting_cast | 717 | 13.987 | 4.619 | 17.387 | 58.356 | 3.888 | 7.370 | 5 | 12.584 | 0.000 | 0.000 |
| pace_possessions | 717 | 13.972 | 4.618 | 17.366 | 58.356 | 3.662 | 7.347 | 3 | 4.033 | -0.015 | -0.001 |
| home_field | 717 | 13.467 | 2.661 | 16.897 | 56.399 | 3.914 | 6.227 | 0 | — | -0.520 | -1.958 |
| clipping | 717 | 13.993 | 4.649 | 17.386 | 58.387 | 3.937 | 7.394 | 7 | 10.373 | 0.006 | 0.030 |
| double_counted_strength | 717 | 13.418 | 2.387 | 16.836 | 56.125 | 2.716 | 6.029 | 0 | — | -0.569 | -2.231 |
| nonlinear_exponent | 717 | 14.062 | 4.830 | 17.463 | 58.568 | 4.021 | 7.523 | 8 | 6.651 | 0.075 | 0.211 |
| efficiency_level | 717 | 14.017 | 4.573 | 17.394 | 58.311 | 1.670 | 7.385 | 0 | — | 0.030 | -0.045 |

## Calibration by predicted-total bin (Val-1)

### Frozen 1.40

| predicted total | n | MAE vs actual | bias vs actual | mean model | mean actual | |m−c| |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| lt_48 | 15 | 12.419 | -4.597 | 44.670 | 49.267 | 5.738 |
| 48_54 | 67 | 11.350 | 1.488 | 51.787 | 50.299 | 6.608 |
| 54_60 | 154 | 14.263 | 5.610 | 57.415 | 51.805 | 7.902 |
| 60_68 | 264 | 16.065 | 9.325 | 63.745 | 54.420 | 11.795 |
| ge_68 | 217 | 20.990 | 17.906 | 73.556 | 55.650 | 17.839 |

### Authorized 0.70 floor

| predicted total | n | MAE vs actual | bias vs actual | mean model | mean actual | |m−c| |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| lt_48 | 2 | 15.340 | 15.340 | 45.340 | 30.000 | 3.090 |
| 48_54 | 87 | 11.780 | 1.392 | 52.151 | 50.759 | 6.812 |
| 54_60 | 385 | 13.724 | 3.397 | 57.155 | 53.758 | 6.988 |
| 60_68 | 238 | 15.012 | 7.517 | 62.454 | 54.937 | 8.212 |
| ge_68 | 5 | 23.344 | 12.584 | 68.984 | 56.400 | 8.184 |

## Offense × defense strength combinations (Val-1)

### Frozen 1.40

| offense tertile × facing defense tertile | n | team-share bias vs actual | mean model total |
| --- | ---: | ---: | ---: |
| off_hi__def_hi | 196 | 11.018 | 63.477 |
| off_hi__def_lo | 125 | 18.581 | 73.469 |
| off_hi__def_mid | 161 | 11.142 | 67.943 |
| off_lo__def_hi | 122 | 4.012 | 55.373 |
| off_lo__def_lo | 190 | 7.954 | 63.512 |
| off_lo__def_mid | 160 | 5.494 | 57.900 |
| off_mid__def_hi | 164 | 8.318 | 59.806 |
| off_mid__def_lo | 155 | 15.417 | 69.256 |
| off_mid__def_mid | 161 | 9.778 | 64.287 |

### Authorized 0.70 floor

| offense tertile × facing defense tertile | n | team-share bias vs actual | mean model total |
| --- | ---: | ---: | ---: |
| off_hi__def_hi | 196 | 5.975 | 58.435 |
| off_hi__def_lo | 125 | 7.784 | 62.672 |
| off_hi__def_mid | 161 | 3.505 | 60.307 |
| off_lo__def_hi | 122 | 2.832 | 54.192 |
| off_lo__def_lo | 190 | 2.645 | 58.203 |
| off_lo__def_mid | 160 | 3.048 | 55.454 |
| off_mid__def_hi | 164 | 5.045 | 56.533 |
| off_mid__def_lo | 155 | 7.027 | 60.865 |
| off_mid__def_mid | 161 | 4.114 | 58.623 |

### Location decomposition — frozen 1.40 (Val-1)

- mean offense index: `1.1356`
- mean defense index: `1.0107`
- mean(off) − mean(def): `0.1249`
- mean raw ratio: `1.1336`
- mean matchup multiplier: `1.1926`
- mean pace: `0.9997`
- mean HFA points: `1.958`
- mean QB index: `1.2282`
- mean off_eff / def_eff: `50.640` / `51.185`
- clamp game rate: `0.0000`
- 2×PPG: `51.800`
- approx matchup lift: `9.978`
- approx pace lift: `-0.016`
- mean HFA added to total: `1.958`

### Location decomposition — authorized 0.70 (Val-1)

- mean offense index: `1.1356`
- mean defense index: `1.0107`
- mean(off) − mean(def): `0.1249`
- mean raw ratio: `1.1336`
- mean matchup multiplier: `1.0871`
- mean pace: `0.9997`
- mean HFA points: `1.958`
- mean QB index: `1.2282`
- mean off_eff / def_eff: `50.640` / `51.185`
- clamp game rate: `0.0000`
- 2×PPG: `51.800`
- approx matchup lift: `4.512`
- approx pace lift: `-0.014`
- mean HFA added to total: `1.958`

## Provenance / limits

- lake mounted: `True`
- Layer A talent: `{'2022': {'n': 131, 'mean': 70.84557251908397}, '2023': {'n': 133, 'mean': 69.40984962406016}, '2024': {'n': 134, 'mean': 68.96350746268656}}`
- sanity: `{"primary": "MULTIPLE", "flags": ["LOCATION", "SCALE", "NONLINEARITY"], "val1_bias": 10.10044630404463, "val1_mae": 16.651408647140865, "mae_minus_abs_bias": 6.550962343096236, "bin_biases": [["lt_48", -4.596666666666668, 15], ["48_54", 1.4883582089552234, 67], ["54_60", 5.610064935064935, 154], ["60_68", 9.324810606060606, 264], ["ge_68", 17.905760368663596, 217]], "high_tail_n": 217, "mean_off_minus_def": 0.12488319386331947, "note": "LOCATION = systematic signed bias. SCALE = error grows with predicted total / O-D gap. NONLINEARITY = tail or exponent pathology. MULTIPLE = more than one is m`

- Score-time overlays only. Production MATCHUP_RESPONSE remains 1.40.
- 0.70 is the authorized floor from PR #545, not an earned coefficient.
- One family at a time. No joint optimization.
- Layer A QB only. Layer B cast/recruiting held out at 50.
- Roster / units / coaching are league-average fills.
- Efficiency is prior-year cfb_ratings.
- HFA is curated 2026 venue proxies.
- 2025 sealed. 2026 excluded. Actual outcomes are the objective.

## GO / STOP

**MULTIVARIATE RECALIBRATION**

STOP. Do not touch 2025, 2026, production CFB, PLAY labels, or Line Curve. Do not write a new production coefficient. Do not resume MATCHUP_RESPONSE sweeps below 0.70.

