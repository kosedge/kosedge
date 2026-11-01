# t5053u — approved metric protocol + stopping rules (PRE-LOOK)

Cite **12763c08 · t5053u · 90774bd4 · 8b80ad7b · 4b9cac5e · 8155fd19 · d7e0a6bc**.

CERT=0 · NFL NO-GO · DRAFT · RETRO_FIT / DEV_RESEARCH.

This protocol is bound **before** any real 2017 outcomes join. It does **not**
authorize a look. `8b80ad7b` was a pre-look tip on prediction-row freeze
`90774bd4` only — it does **not** authorize a look against this final
evaluator freeze. Await a **new** Alex PASS bound to the final freeze sha.

## Primary metric

Paired per-game ΔMAE:

```
δ_i = |cand_i − act_i| − |base_i − act_i|
ΔMAE = mean(δ)
```

- `cand` = `research.q2s.margin_mu_q2s`
- `base` = IF `margin_mu`
- `act` = realized home−away margin (score-only **50bda875** when a look
  is later authorized — **not now**)
- Negative ΔMAE = candidate point improvement
- Do **not** use RMSE, SU, Brier, or market metrics as primary

## Bootstrap

- Paired game-bootstrap of `δ_i`
- **B = 10000**
- **seed = 20261102** (`numpy.random.default_rng(20261102)`)
- Games treated as exchangeable. Repeated-team / week dependence is not modeled.
- CI = percentile [2.5%, 97.5%] of the B resampled means
- Point estimate reported is `mean(δ)` on the observed sample (not the bootstrap mean of means)

## Week-block sensitivity

- **11** blocks: REG weeks **7 through 17** inclusive
- Every block must be present; missing week = refuse
- Per block: n, MAE baseline, MAE candidate, ΔMAE, RMSE baseline/candidate
- Per block: same bootstrap **B=10000 / seed=20261102** (RNG re-seeded per block)
- Week-block numbers are **descriptive / sensitivity only**

## Sample

- n = **141** complete 27/27 rows when a real look is later authorized
- **24 T2** sealed, not scored — stay out
- Examined **70** never pooled
- Silent subsetting is a refuse

## Stopping rules

1. If primary CI contains 0 → verdict **INCONCLUSIVE**. Not FQ PASS.
2. No favorable claim if primary and week-block analyses disagree.
3. Failed or inconclusive result does **not** authorize another weight or a second look.
4. `03a4dd90` stays CLOSED. No re-look of the examined 70.
5. CERT stays 0. No merge / deploy / Stage C / scored-index reuse.
6. LOOK_CONSUMED may be written only after a later CoS re-authorization
   bound to the **final** evaluator freeze sha (not `90774bd4` alone,
   not `8b80ad7b` alone).

## Isolation

Prediction-row freeze `90774bd4` is **history**. Do not rewrite it.
IF mus `32e97434` / q2s `55d8c8bc` / matrix `b56be146` stay unchanged.
Evaluator tests use **synthetic fixtures only**.
