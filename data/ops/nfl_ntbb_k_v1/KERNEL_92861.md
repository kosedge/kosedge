# NTBB-K SYNTHETIC KERNEL — RETURN 36205 / CLEAR 92861 / DESIGN 25194

CERT=0. RESEARCH_ONLY / UNQUALIFIED. DRAFT ≠ merge. Not a fitted-model claim.
Not a new pool. Numeric/direct-boundary only. A integrates later.

| field | value |
|---|---|
| return | **36205** |
| design | **25194** |
| kernel_implemented | **true** (SYNTHETIC law + executed root nine) |
| spec | `2a2c91c9:research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md` sha `2f3c215d…` **MATCH** |
| clarifications | `cc5ce256:research/nfl_followthrough_20261103/NTBB_K_V1_NUMERICAL_CLARIFICATIONS.md` sha `dd2fa8d0…` **MATCH** |
| scipy | **ABSENT** · NOT_EVALUABLE · no install |
| fitting algorithm | **UNEXECUTED_DEPENDENCY_HELD** (future SciPy/L-BFGS-B not replaced, not run) |
| future_grad_step | **5e-6** (not promoted) |
| numeric | stdlib `lgamma` + log-sum-exp + remaining-series NB tail |
| tail | remaining-series bound, first N with upper ≤1e-12 · cap 512 · refuse `NUMERICAL_TAIL_LIMIT` |
| moment | NB(r+1) **same p=r/(r+μ)**, not same mean · bound ≤1e-8 or refuse |
| enumeration_error | \|fsum + tail_est − 1\| ≤ 1e-10 or refuse |
| intervals | DESIGN 25194 clip `[max(0,mass), min(1, mass+tail_upper)]` |
| root nine | **RETURN_36205_ROOT_NINE** · N **175 / 183 / 174** · max **183** = oracle |
| prior demo-small | renamed `DEMO_SMALL_NINE` (μ 4–12, maxN 61) · **not** a root reproduction |
| clocks 143 | **SOURCE_VALUE_MATCH ≠ verified** (EVIDENCE 03972 / 92861 ledger unchanged) |
| owned_completion_claimed | false |

Machine: `KERNEL_SYNTHETIC_92861.json` sha256 `bc71269fd3191ad08f8f4283dd2325c8da49bb3a2d1dfc5f64836ea08c4a341e` (Cos ACCEPT `12c41587`; `ee800291` was `a807af22`, SUPERSEDED).

## Nine-fixture N (executed)

| family | (μ, r, p, c) | tilts | N |
|---|---|---|---|
| MU44_R20 | (44, 20, 0.50, 12) | zero / (0.4,0.7,0.6) / (−0.5,−0.7,−0.6) | **175** |
| MU36_R12 | (36, 12, 0.35, 6) | same three | **183** |
| MU52_R30 | (52, 30, 0.70, 25) | same three | **174** |

## Residuals (max over nine)

normalization / enumeration_error **4.22e-15** · total marginal **2.78e-17** · tail-moment **1.73e-10** (≤ bound **1.74e-10**).

## Extreme refuse/accept (μ=44, p=0.5, c=12)

| r | API | result |
|---|---|---|
| 20 | `enumerate_joint` | **ACCEPT** · N=175 · moments.OK · total_mean 43.99999999985469 |
| 1e12 | `enumerate_joint` | **REFUSE** mass+tail \|2.5847e-05\| > 1e-10 |
| 1e16 | `enumerate_joint` | **REFUSE** mass+tail \|0.68114\| > 1e-10 |

`nbinom_success_p` may still return a representable (p,q). Independent mass+tail / moment checks refuse the collapsed series. No silently different law.

## Interval clip

`event_interval(1, 1e-12) = (1.0, 1.0)`.

## Conditional direct

`conditional_log_mass(0, p=0.5, c=True, k0=NaN, k3=0, k7=0)` **REFUSE** before t=0 shortcut.

## A integrate (12c41587)

- Isolated `NTBB_K_SYNTHETIC_KERNEL_V1` registered · producer→capability/gate ran once
- 143 clocks remain SOURCE_VALUE_MATCH ≠ verified
- SciPy fitting algorithm stays dependency-held
- Package **not** closed from B alone · CERT=0 · no science EXEC
