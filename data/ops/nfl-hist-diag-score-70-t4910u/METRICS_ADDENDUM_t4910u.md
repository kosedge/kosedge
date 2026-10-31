# METRICS_ADDENDUM_t4910u

Add-only from sealed `SCORE_RESULTS.json`. **No IF re-invoke. `simulate_nfl_game` not called.**

Alex RO CONDITIONAL `fbd7abe9` · CoS CLOSE to PASS_DIAG_SCORE · exploratory N=70 · ≠ edge · no CLV.

Machine twin: `METRICS_ADDENDUM_t4910u.json`.

## 1. WP calibration bins (exploratory)

`y_home = 1` if `realized_margin > 0` else `0` (0 ties). Equal-width bins on sealed `forecast_wp_home`.

| WP bin | n | mean forecast WP | empirical home-win rate | |gap| |
|---|---|---|---|---|
| [0.00, 0.40) | 4 | 0.3456 | 0.5000 | 0.1544 |
| [0.40, 0.45) | 9 | 0.4298 | 0.5556 | 0.1258 |
| [0.45, 0.50) | 7 | 0.4793 | 0.5714 | 0.0921 |
| [0.50, 0.55) | 28 | 0.5275 | 0.5000 | 0.0275 |
| [0.55, 0.60) | 11 | 0.5770 | 0.2727 | 0.3043 |
| [0.60, 0.65) | 6 | 0.6230 | 0.8333 | 0.2103 |
| [0.65, 1.00] | 5 | 0.6970 | 0.4000 | 0.2970 |

Sealed WP range 0.3272–0.7040. Mean WP 0.5278 vs mean y 0.5000. Bins with n≤11 are noise. Not a reliability certificate.

## 2. Dispersion envelope

| | forecast_margin | realized_margin |
|---|---|---|
| min | −6.187 | −24.0 |
| p25 | −0.217 | −6.0 |
| median | 1.022 | −1.0 |
| p75 | 2.507 | 9.0 |
| max | 7.796 | 43.0 |
| IQR | 2.724 | 15.0 |
| range | 13.983 | 67.0 |
| sample SD | 2.976 | 13.662 |

IQR ratio (forecast / realized) **0.182**. Range ratio **0.209**. SD ratio **0.218**. Forecast-mean envelope is compressed vs outcomes. Do not expect equality.

## 3. Realized-on-forecast slope (OLS margin)

`realized_margin = 2.223 + (−0.426) × forecast_margin`

- slope **−0.426** · intercept **2.223** · r **−0.093** · R² **0.0086**
- mean forecast 0.993 · mean realized 1.800

Slope is not near 1. Linear association is essentially none at N=70. That is compression / weak mean-signal, not an edge claim. Totals OLS is not the freeze primary (`METRICS_ADDENDUM_t4910u.json`).

## 4. Predictive interval coverage 50 / 80 / 90

**80%** uses sealed draw `p10`–`p90` already in `SCORE_RESULTS` (original 4000-sim quantiles).

**50% / 90%** scale that sealed 80% width (no new draws, no IF call):

`sigma_hat = (p90 − p10) / (2 × z80)` · interval = `mu ± z × sigma_hat`

`z50=0.67449` · `z80=1.28155` · `z90=1.64485` · `mu` = sealed `forecast_margin` / `forecast_total`.

| interval | margin cov (hits/70) | total cov (hits/70) | nominal |
|---|---|---|---|
| 50% | 0.6143 (43) | 0.5000 (35) | 0.50 |
| 80% (sealed p10–p90) | 0.8000 (56) | 0.7429 (52) | 0.80 |
| 90% | 0.8714 (61) | 0.8857 (62) | 0.90 |

Exploratory N=70. Margin 80% matches nominal; total 80% is a bit under. 50/90 inherit the sealed-width scale.

NFL NO-GO · CERT=0
