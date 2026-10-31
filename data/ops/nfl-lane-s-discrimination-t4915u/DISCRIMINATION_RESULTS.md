# DISCRIMINATION_RESULTS — t4915u Lane S

**DEV_RESEARCH / RETRO_FIT exploratory.** CERT=0. NFL NO-GO.
Sealed n=70. n_ties=0. n_complete=70 on every frozen signal. No impute.
All `comparisons_frozen` reported. None dropped for being weak.
Machine-readable twin: `DISCRIMINATION_RESULTS.json`.

Control IF and SCORE_RESULTS **2b9f302e** unchanged. Forecasts not regenerated.

## Control IF (`forecast_margin` vs `realized_margin`)

Known comparator on this sample. Not a retune.

| Stat | Estimate | 95% CI | crosses 0 |
|---|---:|---|---|
| Spearman | −0.098 | [−0.352, 0.144] | yes |
| Pearson | −0.093 | [−0.359, 0.179] | yes |
| OLS slope | −0.426 | [−1.532, 0.680] | yes |
| OLS intercept | 2.223 | [−1.225, 5.671] | — |
| OLS \(R^2\) | 0.009 | | |

SU home-win | IF margin>0: 0.480 (24/50) Wilson [0.348, 0.615].
SU home-win | IF margin<0: 0.550 (11/20) Wilson [0.342, 0.742].
Tertile mean realized margin by IF forecast rank: T1 5.65 (n=23) → T2 0.30 (n=23) → T3 −0.46 (n=24) — **decreasing** (higher IF home mean, lower realized home margin). Descriptive only.

## Frozen signals vs realized_margin

Bootstrap Spearman/Pearson: B=2000, seed=4915, percentile 95%.
OLS: `realized_margin ~ signal`, \(t_{68,0.975}\approx 1.995\).

| Signal | Spearman | Sp 95% CI | Sp×0 | Pearson | OLS slope | OLS slope CI | OLS×0 | \(R^2\) |
|---|---:|---|---|---:|---:|---|---|---:|
| wl_home_wpct | 0.024 | [−0.220, 0.269] | yes | 0.096 | 3.85 | [−5.85, 13.56] | yes | 0.009 |
| wl_away_wpct | 0.198 | [−0.048, 0.430] | yes | 0.213 | 7.96 | [−0.89, 16.81] | yes | 0.045 |
| wl_diff | −0.131 | [−0.378, 0.116] | yes | −0.101 | −3.07 | [−10.40, 4.26] | yes | 0.010 |
| wl_index_off_diff | −0.135 | [−0.381, 0.117] | yes | −0.101 | −14.0 | [−47.3, 19.4] | yes | 0.010 |
| wl_index_def_diff | 0.138 | [−0.113, 0.383] | yes | 0.101 | 15.4 | [−21.3, 52.0] | yes | 0.010 |
| wl_index_net | −0.128 | [−0.373, 0.120] | yes | −0.101 | −154 | [−520, 213] | yes | 0.010 |
| epa_off_diff † | 0.081 | [−0.159, 0.307] | yes | 0.066 | 4.47 | [−12.0, 20.9] | yes | 0.004 |
| epa_def_diff † | −0.097 | [−0.326, 0.153] | yes | −0.152 | −9.80 | [−25.2, 5.61] | yes | 0.023 |
| epa_net_diff † | −0.023 | [−0.283, 0.213] | yes | −0.073 | −3.83 | [−16.5, 8.81] | yes | 0.005 |
| success_off_diff † | 0.140 | [−0.113, 0.370] | yes | 0.132 | 26.8 | [−21.9, 75.6] | yes | 0.017 |
| success_def_diff † | −0.088 | [−0.340, 0.173] | yes | −0.140 | −30.1 | [−81.7, 21.4] | yes | 0.020 |
| success_net_diff † | 0.077 | [−0.172, 0.316] | yes | −0.000 | −0.06 | [−49.0, 48.9] | yes | ~0 |
| matchup_diff_off_epa_5g † | 0.081 | [−0.159, 0.307] | yes | 0.066 | 4.47 | [−12.0, 20.9] | yes | 0.004 |
| matchup_diff_success_rate_5g † | 0.077 | [−0.172, 0.316] | yes | −0.000 | −0.12 | [−98.1, 97.9] | yes | ~0 |

† EPA/success = **RETRO_FIT / DEV_RESEARCH only (A1)**.

**Every** Spearman, Pearson, and OLS slope CI includes 0.

W-L signed diffs (`wl_diff`, `wl_index_off_diff`, `wl_index_net`) have **negative** point estimates (higher home W-L edge, slightly lower realized home margin). `wl_index_def_diff` is the arithmetic flip of the off index (freeze subtraction `away − home`) and therefore the opposite sign. `wl_index_net` OLS slope is large because the net index is O(0.01); \(R^2\) is still 0.01.

## SU home-win rate by signal sign

Exclude `signal==0` and margin ties. Wilson 95%.

| Signal | P(home\|sig>0) | n+ | Wilson + | P(home\|sig<0) | n− | Wilson − | n(sig=0) |
|---|---:|---:|---|---:|---:|---|---:|
| wl_home_wpct | 0.554 | 56 | [0.424, 0.676] | — | 0 | — | 14 |
| wl_away_wpct | 0.481 | 52 | [0.351, 0.613] | — | 0 | — | 18 |
| wl_diff | 0.500 | 22 | [0.307, 0.693] | 0.600 | 20 | [0.387, 0.781] | 28 |
| wl_index_off_diff | 0.500 | 22 | [0.307, 0.693] | 0.600 | 20 | [0.387, 0.781] | 28 |
| wl_index_def_diff | 0.600 | 20 | [0.387, 0.781] | 0.500 | 22 | [0.307, 0.693] | 28 |
| wl_index_net | 0.500 | 22 | [0.307, 0.693] | 0.600 | 20 | [0.387, 0.781] | 28 |
| epa_off_diff † | 0.613 | 31 | [0.438, 0.763] | 0.410 | 39 | [0.271, 0.566] | 0 |
| epa_def_diff † | 0.500 | 32 | [0.336, 0.664] | 0.500 | 38 | [0.348, 0.652] | 0 |
| epa_net_diff † | 0.514 | 35 | [0.356, 0.670] | 0.486 | 35 | [0.330, 0.644] | 0 |
| success_off_diff † | 0.625 | 32 | [0.453, 0.771] | 0.395 | 38 | [0.256, 0.553] | 0 |
| success_def_diff † | 0.462 | 39 | [0.316, 0.614] | 0.548 | 31 | [0.378, 0.708] | 0 |
| success_net_diff † | 0.647 | 34 | [0.479, 0.785] | 0.361 | 36 | [0.225, 0.524] | 0 |
| matchup_diff_off_epa_5g † | 0.613 | 31 | [0.438, 0.763] | 0.410 | 39 | [0.271, 0.566] | 0 |
| matchup_diff_success_rate_5g † | 0.647 | 34 | [0.479, 0.785] | 0.361 | 36 | [0.225, 0.524] | 0 |

`wl_*_wpct` cannot be negative; n−=0 is structural, not a dropped test.
Every Wilson interval that exists **includes 0.50**. The largest raw split is success_net / sealed matchup success (0.647 vs 0.361); both sides still cover 0.50.

## Rank tertiles (mean realized_margin)

Fixed by average rank. No searched cutoffs. T1 = lowest third.

| Signal | T1 n / mean mgn | T2 n / mean mgn | T3 n / mean mgn | mono ↑ | mono ↓ |
|---|---|---|---|---|---|
| wl_home_wpct | 22 / 1.18 | 22 / 3.14 | 26 / 1.19 | no | no |
| wl_away_wpct | 23 / −0.04 | 27 / −0.19 | 20 / 6.60 | no | no |
| wl_diff | 20 / 6.25 | 28 / −0.29 | 22 / 0.41 | no | no |
| wl_index_off_diff | 20 / 6.25 | 28 / −0.29 | 22 / 0.41 | no | no |
| wl_index_def_diff | 22 / 0.41 | 28 / −0.29 | 20 / 6.25 | no | no |
| wl_index_net | 20 / 6.25 | 28 / −0.29 | 22 / 0.41 | no | no |
| epa_off_diff † | 23 / 0.35 | 23 / 1.70 | 24 / 3.29 | **yes** | no |
| epa_def_diff † | 23 / 2.74 | 23 / 0.87 | 24 / 1.79 | no | no |
| epa_net_diff † | 23 / 3.74 | 23 / −1.04 | 24 / 2.67 | no | no |
| success_off_diff † | 23 / 1.83 | 23 / −2.39 | 24 / 5.79 | no | no |
| success_def_diff † | 23 / 2.61 | 23 / 1.78 | 24 / 1.04 | no | **yes** |
| success_net_diff † | 23 / 2.17 | 23 / −0.48 | 24 / 3.63 | no | no |
| matchup_diff_off_epa_5g † | 23 / 0.35 | 23 / 1.70 | 24 / 3.29 | **yes** | no |
| matchup_diff_success_rate_5g † | 23 / 2.17 | 23 / −0.48 | 24 / 3.63 | no | no |

Only `epa_off_diff` / sealed `matchup_diff_off_epa_5g` is monotonically increasing. Spearman CI for that pair still includes 0. W-L tertiles are lumpy because many records tie (T2 of `wl_diff` is 28 zeros).

## Association to IF (`forecast_margin`) — not a retune

| Signal | Spearman vs IF | 95% CI | crosses 0 |
|---|---:|---|---|
| wl_home_wpct | 0.496 | [0.298, 0.657] | no |
| wl_away_wpct | −0.654 | [−0.781, −0.477] | no |
| wl_diff | 0.964 | [0.926, 0.982] | no |
| wl_index_off_diff | 0.963 | [0.926, 0.981] | no |
| wl_index_def_diff | −0.963 | [−0.981, −0.926] | no |
| wl_index_net | 0.964 | [0.926, 0.982] | no |
| epa_off_diff † | 0.499 | [0.304, 0.649] | no |
| epa_def_diff † | 0.417 | [0.207, 0.596] | no |
| epa_net_diff † | 0.793 | [0.664, 0.876] | no |
| success_off_diff † | 0.351 | [0.114, 0.562] | no |
| success_def_diff † | 0.057 | [−0.194, 0.299] | yes |
| success_net_diff † | 0.506 | [0.302, 0.679] | no |
| matchup_diff_off_epa_5g † | 0.499 | [0.304, 0.649] | no |
| matchup_diff_success_rate_5g † | 0.506 | [0.302, 0.679] | no |

W-L signed diffs track sealed IF almost 1:1. That is expected if IF strength is the W-L index map. It is **not** evidence those diffs track outcomes (they do not, on this sample).

## Week-stratified and leave-one-week-out

See `WEEK_SUBSET_AUDIT.md`. Per-week Spearman CIs include 0 for every signed strength signal in every week except the degenerate `wl_home_wpct` (W2 +, W6 −). LOO Spearman ranges are O(0.05–0.36) around near-zero overalls.

## MISSING list

None. Extra RECON games not in the 70 (not expanded): `2017_06_DET_NO`, `2017_06_MIA_ATL`, `2017_06_NYG_DEN`, `2017_06_SF_WAS`.
