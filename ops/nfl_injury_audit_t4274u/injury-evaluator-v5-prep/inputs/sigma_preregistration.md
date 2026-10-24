# C-N1 — σ pre-registration (filed before any v4 run or holdout request)

**Ruling:** IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v2.txt `1a090e3b` C-N1 / N-1  
**Frozen fit HEAD:** `8e2a15ac581277ecda71ea745c3b3477185d733b`  
**fit_object:** `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657` (no `sigma` field)

## σ_margin = 13.5

Source: C-10 default in `services/model-service/src/services/nfl_injury_null_contract.py` at frozen HEAD `8e2a15ac`.

- L339–341: if `baseline_stdev` is missing or `<= 0`, `sigma = 13.5`.
- L410: `sigma_r = sigma_b  # residual must not shrink σ (C-10)`.

This is the margin σ used for primary spread close-vs-outcome and moneyline implied-prob. T-5 still uses σ=13 as written (no √2).

## σ_total = 14.0

Pre-registered here. New choice, not read from fit_object.

- Affects **total** tests only (total close-vs-outcome / ATS / log-loss).
- Does **not** enter the I-3 primary (`spread_clv_delta`) or I-4 VALUE PROVEN path.
- NFL totals residual scale; not imputed from a missing fit field.

Filed before any holdout request. No 2024/25. No CLEAR.
