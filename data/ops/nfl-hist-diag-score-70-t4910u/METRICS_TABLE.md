# METRICS_TABLE

Exploratory at N=70. Benchmarks are labeled baselines ≠ edge proof. No CLV.

| metric | value | caveat |
|---|---|---|
| n_attempted / n_scored / n_failed | 70 / 70 / 0 | all 70 attempted |
| n_decided / n_ties | 70 / 0 | ties reported separately |
| straight-up outcome accuracy (IF) | 0.4714 | NOT ATS-vs-0; no betting line |
| straight-up outcome accuracy (naive W-L) | 0.5000 | baseline ≠ edge |
| straight-up outcome accuracy (pick'em) | 0.5000 | always HOME; baseline ≠ edge |
| MAE / RMSE margin | 10.745 / 14.171 | forecast_margin vs realized_margin |
| MAE / RMSE total | 11.963 / 14.645 | forecast_total vs realized_total |
| MAE / RMSE margin pick'em (0) | 10.486 / 13.683 | baseline |
| MAE / RMSE total const 45.3 | 11.820 / 14.471 | baseline |
| Brier IF / naive W-L / pick'em | 0.2584 / 0.3048 / 0.2500 | exploratory N=70 |
| log-loss IF | 0.7107 | exploratory N=70 |
| sd forecast means / sd realized margin | 2.976 / 13.662 | do not expect equality |
| mean IF sigma | 10.007 | score-error prior; not SD equality |
| coverage margin / total p10–p90 | 0.800 / 0.743 | nominal 0.80; exploratory |
| WP calibration bins | see addendum | exploratory; compressed WP 0.33–0.70 |
| forecast vs realized IQR (margin) | 2.724 / 15.000 | envelope; ratio 0.182 |
| OLS slope realized~forecast margin | −0.426 (r=−0.093) | compression; not edge |
| coverage 50/80/90 margin | 0.614 / 0.800 / 0.871 | 80% sealed draws; 50/90 scaled width |
| coverage 50/80/90 total | 0.500 / 0.743 / 0.886 | same method |

Add-only detail: `METRICS_ADDENDUM_t4910u.md`. Sealed SCORE_RESULTS unchanged. No IF re-invoke.
