# Frozen MATCHUP_RESPONSE=1.40 scoring (v1 universe)

**Generated:** `2026-09-12T02:01:14Z`  
**Contract:** `cfb-qb-feature-v1`  
**MATCHUP_RESPONSE:** `1.4` frozen; scored, not changed  
**Primary label set:** owned Odds-API lake close+actual (lake_only=`True`)  
**Kill switch:** ON. 2025 sealed. 2026 not in the loss. No PLAY.

**Evidence lock:** PR #543 is the current scoring result. PR #542
(`LAKE_NOT_MOUNTED`, Train-0 = 0) is superseded cloud-VM evidence.
Do not copy/densify parquet or spend Odds API credits. See
`cfb-2022-close-recovery-supersedes-542-20260912.md`.

## Decision

**RECALIBRATION JUSTIFIED**

- Val-1 total vs close bias +11.34 ≥ +4
- Val-1 high-tail n=217 total vs close bias +17.79 ≥ +5

Train-0 n=`712` (gate 700). Val-1 n=`717` (gate 700).

Coefficients were **not** moved. Recalibration is **not** performed here.
CFB remains dark.

## Does the inflation / high-tail pathology persist?

Previously observed under *live 2026 v1 serve* (not this hist reconstruction):

{
  "live_2026_w1_total_vs_market_bias": 8.12,
  "live_2026_w2_total_vs_market_bias": 9.94,
  "live_2026_w1_mean_kei_total": 60.67,
  "live_2026_w1_mean_market_total": 52.55,
  "hist_cal_placeholder50_2023_24_total_vs_close_bias": -0.48,
  "hist_cal_placeholder50_spread_vs_close_mae": 8.27,
  "high_tail_definition": 68.0,
  "source": [
    "docs/CFB_TOTALS_HOT_AUDIT.md",
    "data/ops/cfb-p0-residual-audit-20260911.md",
    "data/ops/cfb-historical-calibration-20260805.md",
    "PR #539 / cfb-qb-calibration-protocol-20260911"
  ]
}

This run scores the **same frozen 1.40 formula** on reconstructed `cfb-qb-feature-v1` Layer A (talent center ~70, not placeholder@50) with high-tail = predicted total ≥ 68.0.

Val-1 mean model total `63.838` vs close `52.499` vs actual `53.738`.
Val-1 total vs close bias `11.340`.
Val-1 high-tail n=`217` bias `17.791`.

## Forward-chain splits

### train_0

| Metric | Value |
| --- | ---: |
| n | 712 |
| spread vs close MAE | 7.567 |
| spread vs close RMSE | 9.555 |
| spread vs close bias | 1.458 |
| spread vs close MedAE | 6.275 |
| margin vs actual MAE | 14.133 |
| margin vs actual RMSE | 17.788 |
| margin vs actual bias | -0.821 |
| margin vs actual MedAE | 11.865 |
| total vs close MAE | 12.441 |
| total vs close RMSE | 14.400 |
| total vs close bias | 11.684 |
| total vs close MedAE | 12.090 |
| total vs actual MAE | 17.471 |
| total vs actual RMSE | 21.508 |
| total vs actual bias | 11.888 |
| total vs actual MedAE | 15.535 |
| mean model total | 66.805 |
| mean close total | 55.121 |
| mean actual total | 54.917 |
| mean |model spread| | 8.296 |
| mean |close spread| | 10.895 |
| ATS n | 681 |
| ATS hit | 0.514 |
| ATS ROI −110 | -0.019 |
| O/U n | 698 |
| O/U hit | 0.494 |
| O/U ROI −110 | -0.056 |
| Brier home WP | 0.231 |

Slices:

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 446 | 11.743 | 12.539 | 7.727 | 0.508 | 0.493 |
| home_dog | 266 | 11.587 | 12.277 | 7.297 | 0.524 | 0.496 |
| early_w1_2 | 129 | 10.630 | 10.994 | 7.146 | 0.480 | 0.484 |
| rest_w3_14 | 583 | 11.918 | 12.762 | 7.660 | 0.522 | 0.497 |
| power_vs_power | 305 | 13.268 | 13.642 | 7.960 | 0.481 | 0.488 |
| power_vs_g5 | 114 | 10.228 | 11.052 | 9.817 | 0.464 | 0.513 |
| g5_vs_g5 | 293 | 10.602 | 11.733 | 6.281 | 0.569 | 0.493 |
| high_total_tail_ge_68 | 317 | 15.472 | 15.585 | 8.349 | 0.518 | 0.503 |
| not_high_total_tail | 395 | 8.645 | 9.918 | 6.938 | 0.511 | 0.487 |

Projected-total buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_48 | 4 | 4.193 | 4.778 | 45.443 | 41.250 |
| 48_54 | 35 | 4.964 | 7.792 | 52.178 | 47.214 |
| 54_60 | 107 | 6.375 | 8.723 | 57.188 | 50.813 |
| 60_68 | 249 | 10.209 | 10.813 | 63.944 | 53.735 |
| ge_68 | 317 | 15.472 | 15.585 | 74.183 | 58.711 |

Model-vs-close spread disagreement buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_3 | 187 | 12.048 | 12.685 | 65.831 | 53.783 |
| 3_7 | 197 | 11.156 | 12.218 | 66.078 | 54.921 |
| 7_10 | 125 | 11.127 | 11.998 | 67.139 | 56.012 |
| 10_14 | 111 | 13.117 | 13.499 | 68.454 | 55.338 |
| ge_14 | 92 | 11.106 | 11.751 | 67.899 | 56.793 |

### val_0

| Metric | Value |
| --- | ---: |
| n | 710 |
| spread vs close MAE | 7.554 |
| spread vs close RMSE | 9.617 |
| spread vs close bias | 1.032 |
| spread vs close MedAE | 6.210 |
| margin vs actual MAE | 14.011 |
| margin vs actual RMSE | 17.956 |
| margin vs actual bias | -1.103 |
| margin vs actual MedAE | 11.745 |
| total vs close MAE | 13.429 |
| total vs close RMSE | 15.710 |
| total vs close bias | 12.986 |
| total vs close MedAE | 12.475 |
| total vs actual MAE | 17.793 |
| total vs actual RMSE | 21.830 |
| total vs actual bias | 12.327 |
| total vs actual MedAE | 15.655 |
| mean model total | 65.384 |
| mean close total | 52.398 |
| mean actual total | 53.058 |
| mean |model spread| | 6.782 |
| mean |close spread| | 10.758 |
| ATS n | 669 |
| ATS hit | 0.525 |
| ATS ROI −110 | 0.002 |
| O/U n | 680 |
| O/U hit | 0.504 |
| O/U ROI −110 | -0.037 |
| Brier home WP | 0.208 |

Slices:

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 437 | 13.169 | 13.607 | 7.562 | 0.528 | 0.504 |
| home_dog | 273 | 12.694 | 13.145 | 7.540 | 0.520 | 0.506 |
| early_w1_2 | 108 | 11.428 | 11.512 | 8.739 | 0.569 | 0.476 |
| rest_w3_14 | 602 | 13.266 | 13.773 | 7.341 | 0.517 | 0.510 |
| power_vs_power | 332 | 12.345 | 12.747 | 7.281 | 0.540 | 0.514 |
| power_vs_g5 | 111 | 12.952 | 13.078 | 10.242 | 0.552 | 0.524 |
| g5_vs_g5 | 267 | 13.798 | 14.423 | 6.776 | 0.494 | 0.484 |
| high_total_tail_ge_68 | 267 | 18.487 | 18.522 | 8.141 | 0.532 | 0.504 |
| not_high_total_tail | 443 | 9.671 | 10.360 | 7.200 | 0.520 | 0.505 |

Projected-total buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_48 | 10 | 3.352 | 7.084 | 45.152 | 41.800 |
| 48_54 | 55 | 4.226 | 6.408 | 51.835 | 47.609 |
| 54_60 | 130 | 7.707 | 8.542 | 56.941 | 49.235 |
| 60_68 | 248 | 12.163 | 12.321 | 63.950 | 51.786 |
| ge_68 | 267 | 18.487 | 18.522 | 74.377 | 55.890 |

Model-vs-close spread disagreement buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_3 | 168 | 12.102 | 12.872 | 64.721 | 52.619 |
| 3_7 | 224 | 12.789 | 13.165 | 65.343 | 52.554 |
| 7_10 | 125 | 13.298 | 13.613 | 64.358 | 51.060 |
| 10_14 | 92 | 14.398 | 14.472 | 67.409 | 53.011 |
| ge_14 | 101 | 13.224 | 13.765 | 66.006 | 52.782 |

### train_1

| Metric | Value |
| --- | ---: |
| n | 1422 |
| spread vs close MAE | 7.560 |
| spread vs close RMSE | 9.586 |
| spread vs close bias | 1.246 |
| spread vs close MedAE | 6.230 |
| margin vs actual MAE | 14.072 |
| margin vs actual RMSE | 17.872 |
| margin vs actual bias | -0.962 |
| margin vs actual MedAE | 11.775 |
| total vs close MAE | 12.935 |
| total vs close RMSE | 15.068 |
| total vs close bias | 12.335 |
| total vs close MedAE | 12.215 |
| total vs actual MAE | 17.631 |
| total vs actual RMSE | 21.670 |
| total vs actual bias | 12.107 |
| total vs actual MedAE | 15.570 |
| mean model total | 66.096 |
| mean close total | 53.761 |
| mean actual total | 53.989 |
| mean |model spread| | 7.540 |
| mean |close spread| | 10.826 |
| ATS n | 1350 |
| ATS hit | 0.519 |
| ATS ROI −110 | -0.009 |
| O/U n | 1378 |
| O/U hit | 0.499 |
| O/U ROI −110 | -0.047 |
| Brier home WP | 0.220 |

Slices:

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 883 | 12.449 | 13.068 | 7.646 | 0.518 | 0.498 |
| home_dog | 539 | 12.148 | 12.717 | 7.420 | 0.522 | 0.501 |
| early_w1_2 | 237 | 10.994 | 11.230 | 7.872 | 0.520 | 0.480 |
| rest_w3_14 | 1185 | 12.603 | 13.275 | 7.498 | 0.519 | 0.503 |
| power_vs_power | 637 | 12.787 | 13.175 | 7.606 | 0.511 | 0.502 |
| power_vs_g5 | 225 | 11.572 | 12.051 | 10.026 | 0.507 | 0.518 |
| g5_vs_g5 | 560 | 12.126 | 13.015 | 6.517 | 0.533 | 0.489 |
| high_total_tail_ge_68 | 584 | 16.851 | 16.928 | 8.254 | 0.524 | 0.504 |
| not_high_total_tail | 838 | 9.187 | 10.152 | 7.077 | 0.516 | 0.496 |

Projected-total buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_48 | 14 | 3.592 | 6.425 | 45.235 | 41.643 |
| 48_54 | 90 | 4.513 | 6.946 | 51.968 | 47.456 |
| 54_60 | 237 | 7.105 | 8.623 | 57.053 | 49.947 |
| 60_68 | 497 | 11.184 | 11.566 | 63.947 | 52.763 |
| ge_68 | 584 | 16.851 | 16.928 | 74.272 | 57.421 |

Model-vs-close spread disagreement buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_3 | 355 | 12.074 | 12.774 | 65.306 | 53.232 |
| 3_7 | 421 | 12.025 | 12.722 | 65.687 | 53.662 |
| 7_10 | 250 | 12.213 | 12.805 | 65.749 | 53.536 |
| 10_14 | 203 | 13.697 | 13.940 | 67.981 | 54.283 |
| ge_14 | 193 | 12.214 | 12.805 | 66.908 | 54.694 |

### val_1

| Metric | Value |
| --- | ---: |
| n | 717 |
| spread vs close MAE | 8.123 |
| spread vs close RMSE | 10.339 |
| spread vs close bias | 1.401 |
| spread vs close MedAE | 6.380 |
| margin vs actual MAE | 14.804 |
| margin vs actual RMSE | 18.672 |
| margin vs actual bias | -1.714 |
| margin vs actual MedAE | 12.080 |
| total vs close MAE | 12.177 |
| total vs close RMSE | 14.109 |
| total vs close bias | 11.340 |
| total vs close MedAE | 11.800 |
| total vs actual MAE | 16.651 |
| total vs actual RMSE | 20.429 |
| total vs actual bias | 10.100 |
| total vs actual MedAE | 14.350 |
| mean model total | 63.838 |
| mean close total | 52.499 |
| mean actual total | 53.738 |
| mean |model spread| | 7.242 |
| mean |close spread| | 10.577 |
| ATS n | 682 |
| ATS hit | 0.487 |
| ATS ROI −110 | -0.071 |
| O/U n | 696 |
| O/U hit | 0.522 |
| O/U ROI −110 | -0.004 |
| Brier home WP | 0.231 |

Slices:

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 442 | 11.296 | 12.130 | 8.272 | 0.488 | 0.509 |
| home_dog | 275 | 11.410 | 12.251 | 7.883 | 0.485 | 0.541 |
| early_w1_2 | 119 | 9.931 | 10.899 | 8.170 | 0.531 | 0.443 |
| rest_w3_14 | 598 | 11.620 | 12.431 | 8.114 | 0.478 | 0.537 |
| power_vs_power | 327 | 11.549 | 12.439 | 7.304 | 0.511 | 0.503 |
| power_vs_g5 | 120 | 11.660 | 12.215 | 10.426 | 0.405 | 0.491 |
| g5_vs_g5 | 270 | 10.943 | 11.842 | 8.091 | 0.494 | 0.558 |
| high_total_tail_ge_68 | 217 | 17.791 | 17.839 | 7.702 | 0.475 | 0.491 |
| not_high_total_tail | 500 | 8.540 | 9.719 | 8.306 | 0.492 | 0.535 |

Projected-total buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_48 | 15 | -0.630 | 5.738 | 44.670 | 45.300 |
| 48_54 | 67 | 2.630 | 6.608 | 51.787 | 49.157 |
| 54_60 | 154 | 6.750 | 7.902 | 57.415 | 50.666 |
| 60_68 | 264 | 11.605 | 11.795 | 63.745 | 52.140 |
| ge_68 | 217 | 17.791 | 17.839 | 73.556 | 55.765 |

Model-vs-close spread disagreement buckets:

| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |
| --- | ---: | ---: | ---: | ---: | ---: |
| lt_3 | 166 | 10.924 | 11.913 | 64.057 | 53.133 |
| 3_7 | 223 | 11.470 | 12.203 | 63.887 | 52.417 |
| 7_10 | 103 | 11.543 | 12.274 | 64.543 | 53.000 |
| 10_14 | 99 | 12.864 | 13.067 | 63.713 | 50.848 |
| ge_14 | 126 | 10.291 | 11.700 | 62.986 | 52.694 |

## Year-by-year

### 2022

| Metric | Value |
| --- | ---: |
| n | 712 |
| spread vs close MAE | 7.567 |
| spread vs close RMSE | 9.555 |
| spread vs close bias | 1.458 |
| spread vs close MedAE | 6.275 |
| margin vs actual MAE | 14.133 |
| margin vs actual RMSE | 17.788 |
| margin vs actual bias | -0.821 |
| margin vs actual MedAE | 11.865 |
| total vs close MAE | 12.441 |
| total vs close RMSE | 14.400 |
| total vs close bias | 11.684 |
| total vs close MedAE | 12.090 |
| total vs actual MAE | 17.471 |
| total vs actual RMSE | 21.508 |
| total vs actual bias | 11.888 |
| total vs actual MedAE | 15.535 |
| mean model total | 66.805 |
| mean close total | 55.121 |
| mean actual total | 54.917 |
| mean |model spread| | 8.296 |
| mean |close spread| | 10.895 |
| ATS n | 681 |
| ATS hit | 0.514 |
| ATS ROI −110 | -0.019 |
| O/U n | 698 |
| O/U hit | 0.494 |
| O/U ROI −110 | -0.056 |
| Brier home WP | 0.231 |

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 446 | 11.743 | 12.539 | 7.727 | 0.508 | 0.493 |
| home_dog | 266 | 11.587 | 12.277 | 7.297 | 0.524 | 0.496 |
| early_w1_2 | 129 | 10.630 | 10.994 | 7.146 | 0.480 | 0.484 |
| rest_w3_14 | 583 | 11.918 | 12.762 | 7.660 | 0.522 | 0.497 |
| power_vs_power | 305 | 13.268 | 13.642 | 7.960 | 0.481 | 0.488 |
| power_vs_g5 | 114 | 10.228 | 11.052 | 9.817 | 0.464 | 0.513 |
| g5_vs_g5 | 293 | 10.602 | 11.733 | 6.281 | 0.569 | 0.493 |
| high_total_tail_ge_68 | 317 | 15.472 | 15.585 | 8.349 | 0.518 | 0.503 |
| not_high_total_tail | 395 | 8.645 | 9.918 | 6.938 | 0.511 | 0.487 |

### 2023

| Metric | Value |
| --- | ---: |
| n | 710 |
| spread vs close MAE | 7.554 |
| spread vs close RMSE | 9.617 |
| spread vs close bias | 1.032 |
| spread vs close MedAE | 6.210 |
| margin vs actual MAE | 14.011 |
| margin vs actual RMSE | 17.956 |
| margin vs actual bias | -1.103 |
| margin vs actual MedAE | 11.745 |
| total vs close MAE | 13.429 |
| total vs close RMSE | 15.710 |
| total vs close bias | 12.986 |
| total vs close MedAE | 12.475 |
| total vs actual MAE | 17.793 |
| total vs actual RMSE | 21.830 |
| total vs actual bias | 12.327 |
| total vs actual MedAE | 15.655 |
| mean model total | 65.384 |
| mean close total | 52.398 |
| mean actual total | 53.058 |
| mean |model spread| | 6.782 |
| mean |close spread| | 10.758 |
| ATS n | 669 |
| ATS hit | 0.525 |
| ATS ROI −110 | 0.002 |
| O/U n | 680 |
| O/U hit | 0.504 |
| O/U ROI −110 | -0.037 |
| Brier home WP | 0.208 |

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 437 | 13.169 | 13.607 | 7.562 | 0.528 | 0.504 |
| home_dog | 273 | 12.694 | 13.145 | 7.540 | 0.520 | 0.506 |
| early_w1_2 | 108 | 11.428 | 11.512 | 8.739 | 0.569 | 0.476 |
| rest_w3_14 | 602 | 13.266 | 13.773 | 7.341 | 0.517 | 0.510 |
| power_vs_power | 332 | 12.345 | 12.747 | 7.281 | 0.540 | 0.514 |
| power_vs_g5 | 111 | 12.952 | 13.078 | 10.242 | 0.552 | 0.524 |
| g5_vs_g5 | 267 | 13.798 | 14.423 | 6.776 | 0.494 | 0.484 |
| high_total_tail_ge_68 | 267 | 18.487 | 18.522 | 8.141 | 0.532 | 0.504 |
| not_high_total_tail | 443 | 9.671 | 10.360 | 7.200 | 0.520 | 0.505 |

### 2024

| Metric | Value |
| --- | ---: |
| n | 717 |
| spread vs close MAE | 8.123 |
| spread vs close RMSE | 10.339 |
| spread vs close bias | 1.401 |
| spread vs close MedAE | 6.380 |
| margin vs actual MAE | 14.804 |
| margin vs actual RMSE | 18.672 |
| margin vs actual bias | -1.714 |
| margin vs actual MedAE | 12.080 |
| total vs close MAE | 12.177 |
| total vs close RMSE | 14.109 |
| total vs close bias | 11.340 |
| total vs close MedAE | 11.800 |
| total vs actual MAE | 16.651 |
| total vs actual RMSE | 20.429 |
| total vs actual bias | 10.100 |
| total vs actual MedAE | 14.350 |
| mean model total | 63.838 |
| mean close total | 52.499 |
| mean actual total | 53.738 |
| mean |model spread| | 7.242 |
| mean |close spread| | 10.577 |
| ATS n | 682 |
| ATS hit | 0.487 |
| ATS ROI −110 | -0.071 |
| O/U n | 696 |
| O/U hit | 0.522 |
| O/U ROI −110 | -0.004 |
| Brier home WP | 0.231 |

| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| home_favorite | 442 | 11.296 | 12.130 | 8.272 | 0.488 | 0.509 |
| home_dog | 275 | 11.410 | 12.251 | 7.883 | 0.485 | 0.541 |
| early_w1_2 | 119 | 9.931 | 10.899 | 8.170 | 0.531 | 0.443 |
| rest_w3_14 | 598 | 11.620 | 12.431 | 8.114 | 0.478 | 0.537 |
| power_vs_power | 327 | 11.549 | 12.439 | 7.304 | 0.511 | 0.503 |
| power_vs_g5 | 120 | 11.660 | 12.215 | 10.426 | 0.405 | 0.491 |
| g5_vs_g5 | 270 | 10.943 | 11.842 | 8.091 | 0.494 | 0.558 |
| high_total_tail_ge_68 | 217 | 17.791 | 17.839 | 7.702 | 0.475 | 0.491 |
| not_high_total_tail | 500 | 8.540 | 9.719 | 8.306 | 0.492 | 0.535 |

## Provenance / limits

- lake locate: `{"2022": {"season": 2022, "chosen": "hd_parquet", "mounted": true, "tried": [{"id": "hd_parquet", "path": "/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet", "present": true, "hd_mounted": true}, {"id": "repo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/services/model-service/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet", "present": false}, {"id": "monorepo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet", "present": false}], "raw_rows_loaded": 28322, "raw_rows_season": 28322}, "2023": {"season": 2023, "chosen": "hd_parquet", "mounted": true, "tried": [{"id": "hd_parquet", "path": "/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2023.parquet", "present": true, "hd_mounted": true}, {"id": "repo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/services/model-service/data/cfb/warehouse/clean/odds_cfb/snapshots-2023.parquet", "present": false}, {"id": "monorepo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/data/cfb/warehouse/clean/odds_cfb/snapshots-2023.parquet", "present": false}], "raw_rows_loaded": 28840`
- Layer A talent means: `{'2022': {'n': 131, 'mean': 70.84557251908397}, '2023': {'n': 133, 'mean': 69.40984962406016}, '2024': {'n': 134, 'mean': 68.96350746268656}}`
- skipped: `{'no_universe': 0, 'missing_team': 0, 'ineligible': 637}`
- identity/option: `dropped — prior-year rush/QB-rush tag not built; not proxied from 2026`

- Layer A QB only (talent + class + portal). Layer B cast/recruiting MISSING and held out at 50.
- Roster / units / coaching are league-average fills — same as hist-cal identity layers.
- Efficiency is prior-year cfb_ratings adj EPA, not live SP+.
- HFA is curated 2026 venue proxies.
- Closes: owned Odds-API lake last-legal-pre-kick DK→FD; SDV is fill only and excluded from the primary lake_only score.
- 2025 labels sealed. 2026 W1/W2 not scored.
- Identity/option slice dropped (no prior-year rush tag).

## GO / STOP

**RECALIBRATION JUSTIFIED**

Do not recalibrate in this assignment. Do not unseal 2025. Do not publish a CFB board or PLAY designation.

PR #542 cloud-VM n=0 is superseded. Do not reopen recovery.

