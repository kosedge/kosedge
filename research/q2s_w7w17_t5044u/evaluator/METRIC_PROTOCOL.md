# t5055u — approved metric protocol + stopping rules (PRE-LOOK)

Cite **12763c08 · t5055u · e498fd9f · a4652323 · 5bb525e1 · 90774bd4 · d7e0a6bc**.

CERT=0 · NFL NO-GO · DRAFT · RETRO_FIT / DEV_RESEARCH.

This protocol is bound **before** any real 2017 outcomes join. It does **not**
authorize a look. History freeze **a4652323** and prediction-row freeze
**90774bd4** stay intact. Await an **independent** Alex PASS bound to the
t5055u final freeze sha, then CoS execute under existing authority without
editing evaluator code.

## Primary metric

Paired per-game ΔMAE:

```
δ_i = |cand_i − act_i| − |base_i − act_i|
ΔMAE = mean(δ)   # game-weighted; equivalent to sum(week δ sums)/sum(week n)
```

- `cand` = `research.q2s.margin_mu_q2s`
- `base` = IF `margin_mu`
- `act` = realized home−away margin (score-only **50bda875** when a look
  is later authorized — **not now**)
- Join identity = `(season, week, home, away)` only. No subset.
- n = **141** unique finite paired rows
- Negative ΔMAE = candidate point improvement
- Do **not** use RMSE, SU, Brier, or market metrics as primary

## Game-bootstrap (pooled)

- Paired game-bootstrap of `δ_i`
- **B = 10000**
- **seed = 20261102** (`numpy.random.default_rng(20261102)`)
- Games treated as exchangeable. Repeated-team / week dependence is not modeled.
- CI = percentile [2.5%, 97.5%] of the B resampled means
- Point estimate = observed `mean(δ)` (not the bootstrap mean of means)

## Week-cluster bootstrap (pooled) — t5055u correction

W7–W17 are **11 clusters**. This is **not** a within-week game bootstrap.

For each of B=10000 resamples with RNG seed **20261102**:

1. Sample **11 week indices with replacement**
2. Retain every game in each selected week, including duplicated clusters
3. Statistic = `sum(selected week δ sums) / sum(selected week game counts)`

Report the observed **game-weighted ΔMAE** and the percentile 95% CI.
Compare this pooled week-cluster CI with the pooled game-bootstrap CI.

## Per-week tables

- **11** descriptive blocks: REG weeks **7 through 17** inclusive
- Every block must be present; missing week = refuse
- Per block: n, MAE baseline, MAE candidate, ΔMAE, RMSE baseline/candidate
- **No** per-week bootstrap. **No** requirement that every week have the same sign.

## Sample

- n = **141** complete 27/27 rows when a real look is later authorized
- **24 T2** sealed, not scored — stay out
- Examined **70** never pooled
- Silent subsetting is a refuse

## Stopping rules

1. If **either** pooled CI (game-bootstrap or week-cluster) contains 0 →
   verdict **INCONCLUSIVE**. Not FQ PASS. No favorable conclusion.
2. If the two pooled CIs **disagree in direction** (one entirely < 0, the
   other entirely > 0) → **INCONCLUSIVE**. No favorable conclusion.
3. Do **not** require every individual week same sign.
4. Failed or inconclusive result does **not** authorize another weight or a
   second look.
5. `03a4dd90` stays CLOSED. No re-look of the examined 70.
6. CERT stays 0. No merge / deploy / Stage C / scored-index reuse.
7. LOOK_CONSUMED may be written only after independent Alex receipt **and**
   CoS execute authorization bound to the **t5055u** final freeze sha
   (not `90774bd4` alone, not `a4652323` alone, not `8b80ad7b`).

## look_real path

Complete callable path, still REFUSED without matching receipts:

1. LOOK_CONSUMED absent (single-consumed-look guard)
2. Re-hash complete expected set (parent 90774bd4 + history a4652323 object
   + live t5055u files map)
3. Independent Alex receipt binds live t5055u freeze sha
4. CoS execute authorization binds the same sha
5. Exact pinned score-only identity join; no subset; 141 unique finite pairs
6. Evaluate; write LOOK_CONSUMED once

## Isolation

Prediction-row freeze `90774bd4` is **history**. Do not rewrite it.
History evaluator freeze `a4652323` is **history**. Do not rewrite it.
IF mus `32e97434` / q2s `55d8c8bc` / matrix `b56be146` stay unchanged.
Evaluator tests use **synthetic fixtures only**. No real 2017 outcomes join
in tests.
