# RECEIPT_RETURN36205_B

CERT=0. Cos ORDER RETURN 36205 under CLEAR 92861 / DESIGN 25194.
ACK≠START. Fresh GATE0. Not a new pool. C1–C8 mid-flight folded (no C1C8 commit existed).
Worker B · numeric/direct boundary only. A integrates later. **No whole-package close.**

| field | value |
|---|---|
| return | 36205 |
| design | 25194 |
| clear | 92861 |
| worker | B · bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| GATE0 | **PASS** · 2026-11-04T00:04:55Z · tip `d0bb6bef` **MATCH** |
| GATE0 receipt | `START_PREFLIGHT_RETURN36205_B.md` sha `a6b313c8…` |
| clarifications | cc5ce256 · sha **MATCH** `dd2fa8d041b652324c07b77aea2f2b589146213342a414b98e8bcc629d5bc3e8` |
| spec | 2a2c91c9 · sha **MATCH** `2f3c215d…` |
| tests | **36 passed REPORTED_ONLY** (21 owned + 15 kernel) |
| clocks 143 | SOURCE_VALUE_MATCH ≠ verified (not promoted) |
| owned_completion_claimed | false |
| package_close | false |

## Nine-fixture N

175 / 183 / 174 (MU44_R20 / MU36_R12 / MU52_R30 × three tilt packets).
Prior B maxN 61 (μ 4–12) renamed `DEMO_SMALL_NINE` — **not** a root reproduction.

## Extreme refuse/accept (μ=44, p=0.5, c=12)

| r | result | detail |
|---|---|---|
| 20 | **ACCEPT** | N=175 · moments.OK · mean 43.99999999985469 · enum_err 1.22e-15 |
| 1e12 | **REFUSE** | mass+tail \|2.5847e-05\| > 1e-10 |
| 1e16 | **REFUSE** | mass+tail \|0.68114\| > 1e-10 |

## Interval clip

`event_interval(1, 1e-12) → (1.0, 1.0)`.

## Conditional

NaN / bool refused **before** t=0 shortcut.

## Residuals (max over nine)

enum/norm 4.22e-15 · marginal 2.78e-17 · tail-moment 1.73e-10 ≤ bound 1.74e-10.

## Held

No install · no real fit/data · no science EXEC · 143 clocks not promoted · future_grad_step 5e-6 not promoted.
