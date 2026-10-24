# Holdout gate table (no values)

**Ruling:** `b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt`  
**Decision:** `fabf8732` / `t4335s14919`  
**Scorer:** `ca98ae0e` (imported by sha; seed 20261023; σ 13.5 / 14.0)  
**Holdout values:** none. Opening is not permitted.

Verbatim from `a156459b` s6/s7:

```
I-1  Paired comparison, adjusted vs base, same games, priced at the same as_of_ts, against
     the CLOSING line: CLV (points and implied-prob), ATS win rate, log-loss delta.
I-2  Minimum sample: >= 500 games with a non-zero adjustment in the sealed holdout and
     >= 2 full seasons; below that the result is INCONCLUSIVE (no claim).
I-3  Multiple comparisons: 3 markets x 3 metrics = 9 tests; Holm-Bonferroni at family
     alpha 0.05. Primary endpoint = mean CLV delta (spread) - stated now, not chosen later.
I-4  Decision rule: VALUE PROVEN only if primary endpoint significant after Holm, its 95%
     block-bootstrap CI excludes 0, and K-4 passes. Anything else = NO CLAIM.
I-5  Soft, borderline or insignificant results cannot become a product claim, marketing
     copy, or a "improves accuracy" statement. Report them as null results.
```

```
K-2  Metrics, base vs adjusted on the same games: Brier and log loss (win prob);
     cover reliability for spread and total (predicted cover prob vs actual);
     reliability diagram in 10 bins with counts.
K-3  CIs: block bootstrap by NFL week, 10,000 resamples, 95% percentile CI, paired.
K-4  Gate: adjusted must not be worse than base: upper 95% CI of (adj - base) log loss
     <= 0.002 and Brier <= 0.0005. Calibration slope of adjusted within [0.9, 1.1].
     Failing = layer stays off.
```

VALUE PROVEN also requires primary CI **lo > 0**. No-pick ATS is **None**.
I-1 “CLV” is scored as **close vs outcome**. Label: **comparative research, not certified CLV**.
