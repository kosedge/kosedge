# MATCHUP_RESPONSE coefficient sweep (v1 universe)

**Generated:** `2026-09-12T03:38:49Z`  
**Contract:** `cfb-qb-feature-v1`  
**Production MATCHUP_RESPONSE:** `1.4` (unchanged)  
**Sweep:** score-time overlay only. Early-season soften still applies.  
**Primary objective:** actual outcomes. Close is a benchmark, not the target.  
**Kill switch:** ON. 2025 sealed. 2026 not in the loss. No PLAY. No Line Curve.

## Decision

**BROADER MODEL RECALIBRATION REQUIRED**

Best-candidate region:

- `val1_mae_vs_actual_min` = `0.7`
- `val1_abs_bias_vs_actual_min` = `0.7`
- `val1_rmse_vs_actual_min` = `0.7`
- `train0_mae_vs_actual_min` = `0.7`
- `val0_mae_vs_actual_min` = `0.7`

- Val-1 MAE vs actual still minimized at the floor (0.70)
- response would have to leave the authorized neighborhood of 1.40

Production `priors.MATCHUP_RESPONSE` was **not** written. CFB remains dark. 2025 remains sealed.

## Sensitivity table

MAE / bias columns are **vs actual** unless labeled close. Do not read a smaller |model−close| as a better football model.

| r | phase | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / RMSE / bias / MedAE | Val-1 vs close bias / |m−c| | tail n / act-bias / close-bias | ATS / ROI |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 0.70 | extend_low | 712 / 14.380 / 4.791 | 710 / 14.566 / 6.022 | 717 / 13.987 / 17.387 / 4.619 / 12.100 | 5.858 / 7.370 | 5 / 12.584 / 8.184 | 0.493 / -0.059 |
| 0.72 | refine | 712 / 14.422 / 4.975 | 710 / 14.624 / 6.186 | 717 / 14.034 / 17.436 / 4.761 / 12.130 | 6.000 / 7.475 | 5 / 13.038 / 8.638 | 0.490 / -0.065 |
| 0.74 | refine | 712 / 14.465 / 5.160 | 710 / 14.685 / 6.351 | 717 / 14.083 / 17.489 / 4.904 / 12.130 | 6.144 / 7.583 | 10 / 9.516 / 9.816 | 0.492 / -0.061 |
| 0.75 | extend_low | 712 / 14.487 / 5.253 | 710 / 14.716 / 6.434 | 717 / 14.108 / 17.516 / 4.976 / 12.100 | 6.215 / 7.637 | 11 / 9.765 / 9.902 | 0.493 / -0.059 |
| 0.80 | extend_low | 712 / 14.602 / 5.722 | 710 / 14.876 / 6.852 | 717 / 14.240 / 17.658 / 5.339 / 12.210 | 6.579 / 7.918 | 19 / 11.332 / 10.858 | 0.491 / -0.064 |
| 0.85 | extend_low | 712 / 14.737 / 6.198 | 710 / 15.048 / 7.276 | 717 / 14.380 / 17.813 / 5.707 / 12.210 | 6.946 / 8.211 | 28 / 15.144 / 11.447 | 0.492 / -0.061 |
| 0.90 | coarse | 712 / 14.894 / 6.680 | 710 / 15.232 / 7.706 | 717 / 14.533 / 17.983 / 6.080 / 12.300 | 7.319 / 8.516 | 35 / 15.109 / 11.895 | 0.493 / -0.058 |
| 0.95 | coarse | 712 / 15.064 / 7.168 | 710 / 15.430 / 8.141 | 717 / 14.696 / 18.165 / 6.458 / 12.650 | 7.697 / 8.830 | 55 / 13.551 / 12.251 | 0.493 / -0.058 |
| 1.00 | coarse | 712 / 15.248 / 7.664 | 710 / 15.638 / 8.582 | 717 / 14.871 / 18.360 / 6.841 / 12.780 | 8.081 / 9.159 | 71 / 13.931 / 12.995 | 0.495 / -0.055 |
| 1.05 | coarse | 712 / 15.450 / 8.167 | 710 / 15.859 / 9.029 | 717 / 15.059 / 18.570 / 7.230 / 13.080 | 8.469 / 9.497 | 92 / 14.069 / 13.748 | 0.495 / -0.055 |
| 1.10 | coarse | 712 / 15.673 / 8.676 | 710 / 16.094 / 9.481 | 717 / 15.257 / 18.794 / 7.624 / 13.220 | 8.863 / 9.847 | 111 / 14.562 / 14.449 | 0.497 / -0.051 |
| 1.15 | coarse | 712 / 15.920 / 9.193 | 710 / 16.343 / 9.940 | 717 / 15.463 / 19.031 / 8.023 / 13.380 | 9.262 / 10.209 | 129 / 14.818 / 14.993 | 0.496 / -0.052 |
| 1.20 | coarse | 712 / 16.190 / 9.717 | 710 / 16.604 / 10.405 | 717 / 15.681 / 19.283 / 8.427 / 13.480 | 9.666 / 10.583 | 142 / 16.159 / 15.515 | 0.496 / -0.052 |
| 1.25 | coarse | 712 / 16.480 / 10.249 | 710 / 16.883 / 10.876 | 717 / 15.910 / 19.548 / 8.837 / 13.780 | 10.076 / 10.969 | 160 / 17.101 / 15.983 | 0.493 / -0.059 |
| 1.30 | coarse | 712 / 16.793 / 10.787 | 710 / 17.172 / 11.353 | 717 / 16.149 / 19.828 / 9.252 / 14.130 | 10.491 / 11.362 | 182 / 17.256 / 16.676 | 0.493 / -0.059 |
| 1.35 | coarse | 712 / 17.127 / 11.334 | 710 / 17.473 / 11.837 | 717 / 16.397 / 20.121 / 9.674 / 14.140 | 10.913 / 11.766 | 202 / 17.296 / 17.207 | 0.489 / -0.066 |
| 1.40 | coarse | 712 / 17.471 / 11.888 | 710 / 17.793 / 12.327 | 717 / 16.651 / 20.429 / 10.100 / 14.350 | 11.340 / 12.177 | 217 / 17.906 / 17.791 | 0.487 / -0.071 |

## Comparison vs frozen 1.40 (Val-1)

| Metric | candidate | frozen 1.40 | Δ |
| --- | ---: | ---: | ---: |
| n | 717 | 717 | 0.000 |
| MAE vs actual | 13.987 | 16.651 | -2.664 |
| RMSE vs actual | 17.387 | 20.429 | -3.042 |
| bias vs actual | 4.619 | 10.100 | -5.482 |
| MedAE vs actual | 12.100 | 14.350 | -2.250 |
| bias vs close (diagnostic) | 5.858 | 11.340 | -5.482 |
| MAE vs close (diagnostic) | 7.370 | 12.177 | -4.806 |
| mean |model−close| | 7.370 | 12.177 | -4.806 |
| high-tail n (≥68) | 5 | 217 | -212.000 |
| high-tail bias vs actual | 12.584 | 17.906 | -5.322 |
| high-tail bias vs close | 8.184 | 17.791 | -9.607 |
| mean model total | 58.356 | 63.838 | -5.482 |
| mean actual total | 53.738 | 53.738 | 0.000 |
| mean close total | 52.499 | 52.499 | 0.000 |
| ATS hit | 0.493 | 0.487 | 0.006 |
| ATS ROI −110 | -0.059 | -0.071 | 0.011 |
| margin MAE vs actual | 14.888 | 14.804 | 0.084 |

## Tail inflation

No earned candidate. Frozen 1.40 tail remains the reference:

- n=`217`
- bias vs actual `17.906`
- bias vs close `17.791`

### Val-1 disagreement buckets (frozen 1.40)

| |model−close| bucket | n | MAE vs actual | bias vs actual | ATS |
| --- | ---: | ---: | ---: | ---: |
| lt_3 | 80 | 14.773 | 1.430 | 0.526 |
| 3_7 | 107 | 10.864 | 1.799 | 0.515 |
| 7_10 | 104 | 14.480 | 6.324 | 0.557 |
| 10_14 | 153 | 15.863 | 8.855 | 0.429 |
| ge_14 | 273 | 20.739 | 18.031 | 0.471 |

## Provenance / limits

- lake mounted: `True`
- lake locate: `{"2022": {"season": 2022, "chosen": "hd_parquet", "mounted": true, "tried": [{"id": "hd_parquet", "path": "/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet", "present": true, "hd_mounted": true}, {"id": "repo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/services/model-service/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet", "present": false}, {"id": "monorepo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet", "present": false}], "raw_rows_loaded": 28322, "raw_rows_season": 28322}, "2023": {"season": 2023, "chosen": "hd_parquet", "mounted": true, "tried": [{"id": "hd_parquet", "path": "/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2023.parquet", "present": true, "hd_mounted": true}, {"id": "repo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/services/model-service/data/cfb/warehouse/clean/odds_cfb/snapshots-2023.parquet", "present": false}, {"id": "monorepo_parquet", "path": "/Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/data/cfb/warehouse/clean/odds_cfb/snapshots-2023.parquet", "present": false}], "raw_rows_loaded": 28840`
- Layer A talent: `{'2022': {'n': 131, 'mean': 70.84557251908397}, '2023': {'n': 133, 'mean': 69.40984962406016}, '2024': {'n': 134, 'mean': 68.96350746268656}}`
- sanity: `{"ok": true, "why": [], "observed": {"n": 717, "bias_vs_close": 11.339637377963736, "high_tail_bias_vs_close": 17.790552995391707, "bias_vs_actual": 10.10044630404463}, "published": {"n": 717, "bias_vs_close": 11.34, "high_tail_bias_vs_close": 17.79, "bias_vs_actual": 10.1, "source": "PR #543 / data/ops/cfb-frozen-140-scoring-20260912.json"}}`

- Only MATCHUP_RESPONSE is overlaid at score time. Production constant remains 1.40.
- Early-season soften (W1=0.90 / W2=0.93 / W3=0.96 / W4=0.98) still multiplies the candidate.
- Layer A QB only. Layer B cast/recruiting held out at 50.
- 2025 sealed. 2026 not used for selection.
- Selection does not minimize |model−close|. A model at 61 can beat a close of 52 when the game finishes 66.

## GO / STOP

**BROADER MODEL RECALIBRATION REQUIRED**

STOP. Do not touch 2025, 2026, production CFB, PLAY labels, or Line Curve. Do not write a new production coefficient in this assignment.

