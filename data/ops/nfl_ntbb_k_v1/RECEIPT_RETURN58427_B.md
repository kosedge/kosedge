# RECEIPT_RETURN58427_B + ADDITIVE 80649

CERT=0. RETURN 58427 under 36205. ADDITIVE 80649 fold-in. Direct probability/tail/BB proof only.
Not a new pool. No full re-review. A integrates later. **No package close.**

| field | value |
|---|---|
| return | 58427 |
| under | 36205 |
| additive | 80649 |
| GATE0 | **PASS** · 2026-11-04T00:29:15Z · start tip `a807af22` **MATCH** |
| tests | **39 passed REPORTED_ONLY** |
| clocks 143 | SOURCE_VALUE_MATCH ≠ verified |
| CSV44 | staged separately — **not** a kernel correction |
| package_close | false |

## log_joint_pmf / NB extreme matrix (μ=44, p=0.5, c=12)

| r | `log_joint_pmf(0,0)` | `log_nbinom_pmf` / `nbinom_success_p` | `enumerate_joint` |
|---|---|---|---|
| 20 | **ACCEPT** −23.263016196113618 (bit-identical) | ACCEPT | ACCEPT N=175 |
| 1e12 | **REFUSE** UNSUPPORTED_NUMERIC_DOMAIN | REFUSE | REFUSE |
| 1e16 | **REFUSE** UNSUPPORTED_NUMERIC_DOMAIN | REFUSE | REFUSE |

Shared entrypoint: float64 `r*log(p)` vs `-r*log1p(μ/r)` > 1e-8. No fabricated corrected log-PMF.

## Tail fixture (n=0.5, p=q=0.5, cutoff=0)

| quantity | value |
|---|---|
| invalid first/(1−ρ), ρ=0.375 | 0.282842712474619 < true 0.2928932188134524 |
| certified ρ_bound = max(q,ρ) = 0.5 | first/(1−0.5) = **0.3535533905932735** ≥ true |
| moment r=0.5 | same p=0.5, r+1=1.5, same_mean=false |

## BB / conditional extreme matrix (t=2, p=0.3, k=0)

| c | `conditional_log_mass` | mean vs t*p=0.6 |
|---|---|---|
| 12 | **ACCEPT** probs [0.5061538461538465, 0.3876923076923073, 0.10615384615384624] | 0.5999999999999998 |
| 1e12 | **REFUSE** lgamma rising ≠ recurrence | (was 0.599844 — cancelled) |
| 1e16 | **REFUSE** lgamma rising ≠ recurrence | (was 1.0 — cancelled) |

`log_betabinom_pmf` and `log_joint_pmf(..., c=1e16)` refuse on the same shared BB check.

## Ordinary positive unchanged

root-nine N **175 / 183 / 174** PASS · log_joint_pmf(0,0) pins bit-identical · interval clip (1, 1e-12)→(1,1) · NaN/bool refuse before t=0.

## Residuals (max over nine)

enum/norm 4.22e-15 · marginal 2.78e-17 · tail-moment 1.73e-10.
