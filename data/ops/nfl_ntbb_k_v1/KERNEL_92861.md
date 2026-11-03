# NTBB-K SYNTHETIC KERNEL — CLEAR 92861 / METADATA 14083

CERT=0. RESEARCH_ONLY / UNQUALIFIED. DRAFT ≠ merge. Not a fitted-model claim.

| field | value |
|---|---|
| kernel_implemented | **true** (SYNTHETIC law + nine cases only) |
| spec | `2a2c91c9:research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md` sha `2f3c215d…` **MATCH** |
| scipy | **ABSENT** · NOT_EVALUABLE · no install |
| fitting algorithm | **UNEXECUTED_DEPENDENCY_HELD** (future SciPy/L-BFGS-B not replaced, not run) |
| numeric | stdlib `lgamma` + log-sum-exp + NB recurrence |
| tail | first N with P(T>N)≤1e-12 · cap 512 · refuse NUMERICAL_TAIL_LIMIT |
| moment | bound ≤1e-8 or refuse moments · no silent renormalize |
| root nine | **PASS** · max enumerated total **61** · oracle max **183** honored |
| clocks 143 | **SOURCE_VALUE_MATCH ≠ verified** (EVIDENCE 03972 / 92861 ledger unchanged) |
| owned_completion_claimed | false |

Machine: `KERNEL_SYNTHETIC_92861.json` sha256 `2d12f9d180d30b25547ff8ac4cbac24c48258f058e680211a47e70296a3de498`.

## Residuals (max over nine)

normalization ≤1e-16 · symmetry/transpose ≤5e-17 · total marginal ≤3e-17 · tail-moment ≤6e-11 · moment bound ≤6e-11.

## What remains for A

- Register isolated `NTBB_K_SYNTHETIC_KERNEL_V1` on shared evidence gate if A chooses
- Consume METADATA 14083 independently
- Do not treat B 143 SOURCE_VALUE_MATCH as verified clocks
- SciPy fitting algorithm stays dependency-held
- No science EXEC / no real 2014–19 fit
