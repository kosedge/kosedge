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

Coverage uses sealed-sim-equivalent draws: `random.Random(seed)` + `max(0, gauss(mean, sigma))` — the only RNG consumer in `simulate_nfl_game` at 6ca03716. Replay means come from IF diagnostics rounded to 3 d.p., so mu identity is ~1e-3 not bit-exact. Coverage intervals still use those sealed rounded means + sigma.
