# COMPRESSION_HIST_DIAG

Forecast-margin SD is the dispersion of **means**. Realized-margin SD includes outcome noise. Do not expect equality.

| quantity | value | meaning |
|---|---|---|
| sd_forecast_means | 2.9762 | sample SD of 70 forecast margins |
| sd_realized_margin | 13.6622 | sample SD of 70 realized margins |
| mean_if_sigma | 10.0068 | mean per-game IF score-error sigma |
| coverage_margin_p10_p90 | 0.8000 | share of realized margins inside sealed-sim p10–p90 |
| coverage_total_p10_p90 | 0.7429 | share of realized totals inside sealed-sim p10–p90 |
| draw_replay_max_abs_err_margin | 0.000891 | IF mu vs replayed draws (identity) |
| draw_replay_max_abs_err_total | 0.000985 | IF mu vs replayed draws (identity) |
| forecast IQR / range | 2.724 / 13.983 | sealed forecast-mean envelope |
| realized IQR / range | 15.000 / 67.000 | outcome envelope |
| IQR ratio (forecast/realized) | 0.182 | compression |
| OLS slope / r (margin) | −0.426 / −0.093 | realized-on-forecast; N=70 |
| coverage 50/80/90 margin | 0.614 / 0.800 / 0.871 | 80% sealed p10–p90; 50/90 scaled |
| coverage 50/80/90 total | 0.500 / 0.743 / 0.886 | same |

80% coverage is the sealed-sim p10–p90 already in SCORE_RESULTS. 50/90 scale that width from sealed mu (no IF re-invoke). See `METRICS_ADDENDUM_t4910u.md`.
