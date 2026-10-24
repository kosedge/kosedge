# Evaluator dry-run report

**Generated:** deterministic (seed=2708041115; no wall-clock)
**Frozen-fit HEAD:** `8e2a15ac581277ecda71ea745c3b3477185d733b`
**Run HEAD:** `2241af8e9dcc1b6446ba4b0b9e73ab159762b05a`
**Spec:** `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`
**Export:** `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8`
**Fit object:** `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657`
**Seed:** `2708041115`  n_boot=10000
**Close proxy:** comparative research, not certified CLV
**Holdout:** STOPPED (Ryan t4315u `d6fca6f0`). No CLEAR. 2024–25 not opened.
**Readiness:** Ryan t4317u / decision `5c4e6578`. Checker: t4320u.

Command (no secrets):

```
python3 /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/run_injury_residual_evaluator.py --out /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/out --cohorts synthetic_inconclusive,synthetic_fail,synthetic_pass,le2023
```

## I-1..I-5 and K-2..K-4 (verbatim)

- I-1. Paired comparison, adjusted vs base, same games, priced at the same as_of_ts, against the CLOSING line: CLV (points and implied-prob), ATS win rate, log-loss delta.
- I-2. Minimum sample: >= 500 games with a non-zero adjustment in the sealed holdout and >= 2 full seasons; below that the result is INCONCLUSIVE (no claim).
- I-3. Multiple comparisons: 3 markets x 3 metrics = 9 tests; Holm-Bonferroni at family alpha 0.05. Primary endpoint = mean CLV delta (spread) - stated now, not chosen later.
- I-4. Decision rule: VALUE PROVEN only if primary endpoint significant after Holm, its 95% block-bootstrap CI excludes 0, and K-4 passes. Anything else = NO CLAIM.
- I-5. Soft, borderline or insignificant results cannot become a product claim, marketing copy, or a "improves accuracy" statement. Report them as null results.
- K-2. Metrics, base vs adjusted on the same games: Brier and log loss (win prob); cover reliability for spread and total (predicted cover prob vs actual); reliability diagram in 10 bins with counts.
- K-3. CIs: block bootstrap by NFL week, 10,000 resamples, 95% percentile CI, paired.
- K-4. Gate: adjusted must not be worse than base: upper 95% CI of (adj - base) log loss <= 0.002 and Brier <= 0.0005. Calibration slope of adjusted within [0.9, 1.1]. Failing = layer stays off.

Primary = mean CLV delta (spread). 9 tests = 3 markets × 3 metrics. Non-zero adjustment = Δmargin≠0 or Δtotal≠0. I-4 VALUE PROVEN only if primary Holm-significant AND CI excludes 0 AND K-4 passes.

## Cohort `synthetic_inconclusive`

Known answer: I-2 shortfall (1 season, n_nonzero<500) → INCONCLUSIVE.

- I-2: `INCONCLUSIVE` — n_nonzero_adjustment=20 by_season={2018: 20} full_seasons=0
- I-4 decision: **INCONCLUSIVE** (primary_holm=False, CI_excludes_0=False, k4=False)
- Product claim: False (null results reported as null; no product claim)
- Identical cohort n=40 ; paired both-CLV n=40
- Missing: incomplete=0 close=0 actual=0 baseline=0
- Missing by season: incomplete={} close={} actual={} baseline={}
- Universe by season: {2018: 40}
- edge=0 drops: base=0 adj=0
- K-4: logloss_CI_hi=-0.010730715907124655 brier_CI_hi=-0.00533961516296394 slope=None pass=False ['slope undefined (need >=2 occupied reliability bins); K-4 fail']

### I-1 metrics (adj − base)

| metric | value |
|---|---|
| `spread_clv_delta` | 0.0 |
| `spread_ats_delta` | 0.0 |
| `spread_logloss_delta` | 0.010348162256727633 |
| `total_clv_delta` | undefined — no row with both arms defined for this metric (usually edge=0 on that market); not a stub |
| `total_ats_delta` | 0.0 |
| `total_logloss_delta` | 0.008710311397799542 |
| `ml_clv_implied_prob_delta` | 0.0 |
| `ml_ats_delta` | 0.0 |
| `ml_logloss_delta` | -0.010730715907124655 |

### K-2 win-prob

- Brier base=0.2220669249803094 adj=0.21672730981734545
- log loss base=0.6372202096199495 adj=0.6264894937128249

### I-3 Holm (α=0.05)

| test | p | rank | threshold | significant |
|---|---|---|---|---|
| `spread_logloss_delta` | 0.0 | 1 | 0.005555555555555556 | True |
| `total_logloss_delta` | 0.0 | 2 | 0.00625 | True |
| `ml_logloss_delta` | 0.0 | 3 | 0.0071428571428571435 | True |
| `spread_clv_delta` | 1.0 | 4 | 0.008333333333333333 | False |
| `spread_ats_delta` | 1.0 | 5 | 0.01 | False |
| `total_clv_delta` | 1.0 | 6 | 0.0125 | False |
| `total_ats_delta` | 1.0 | 7 | 0.016666666666666666 | False |
| `ml_clv_implied_prob_delta` | 1.0 | 8 | 0.025 | False |
| `ml_ats_delta` | 1.0 | 9 | 0.05 | False |

### K-3 primary CI

spread_clv_delta obs=0.0 CI=[0.0, 0.0] excludes_0=False p=1.0 blocks=4 seed=2708041115

### Reliability bins (K-2, 10 bins, counts)

**spread**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 0 | None | None | bin empty; not a stub |
| 2 | 0 | None | None | bin empty; not a stub |
| 3 | 0 | None | None | bin empty; not a stub |
| 4 | 40 | 0.44833731676017125 | 0.0 |  |
| 5 | 0 | None | None | bin empty; not a stub |
| 6 | 0 | None | None | bin empty; not a stub |
| 7 | 0 | None | None | bin empty; not a stub |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 0 | None | None | bin empty; not a stub |

**total**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 0 | None | None | bin empty; not a stub |
| 2 | 0 | None | None | bin empty; not a stub |
| 3 | 0 | None | None | bin empty; not a stub |
| 4 | 0 | None | None | bin empty; not a stub |
| 5 | 40 | 0.5043174402629403 | 0.0 |  |
| 6 | 0 | None | None | bin empty; not a stub |
| 7 | 0 | None | None | bin empty; not a stub |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 0 | None | None | bin empty; not a stub |

**ml**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 0 | None | None | bin empty; not a stub |
| 2 | 0 | None | None | bin empty; not a stub |
| 3 | 0 | None | None | bin empty; not a stub |
| 4 | 0 | None | None | bin empty; not a stub |
| 5 | 40 | 0.5344955250945402 | 1.0 |  |
| 6 | 0 | None | None | bin empty; not a stub |
| 7 | 0 | None | None | bin empty; not a stub |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 0 | None | None | bin empty; not a stub |

Baseline and adjusted used the **same** identical-close cohort. No arm-specific drop after scoring started.

## Cohort `synthetic_fail`

Known answer: 2 full seasons, n>=500, adj worse → I-4 NO CLAIM (FAIL).

- I-2: `MET` — n_nonzero_adjustment=612 by_season={2018: 306, 2019: 306} full_seasons=2
- I-4 decision: **NO CLAIM** (primary_holm=True, CI_excludes_0=True, k4=False)
- Product claim: False (null results reported as null; no product claim)
- Identical cohort n=612 ; paired both-CLV n=612
- Missing: incomplete=0 close=0 actual=0 baseline=0
- Missing by season: incomplete={} close={} actual={} baseline={}
- Universe by season: {2018: 306, 2019: 306}
- edge=0 drops: base=0 adj=0
- K-4: logloss_CI_hi=0.08720461012603105 brier_CI_hi=0.034383504214631766 slope=0.9990752469489775 pass=False ['logloss_CI_hi 0.08720461012603105 > 0.002', 'brier_CI_hi 0.034383504214631766 > 0.0005']

### I-1 metrics (adj − base)

| metric | value |
|---|---|
| `spread_clv_delta` | -0.06045751633986928 |
| `spread_ats_delta` | -0.06045751633986928 |
| `spread_logloss_delta` | -0.031756081811972356 |
| `total_clv_delta` | 1.8169934640522876 |
| `total_ats_delta` | -0.4542483660130719 |
| `total_logloss_delta` | 0.2583094854484915 |
| `ml_clv_implied_prob_delta` | 0.05009680413208014 |
| `ml_ats_delta` | -0.10130718954248366 |
| `ml_logloss_delta` | 0.08052603154006754 |

### K-2 win-prob

- Brier base=0.1439389888469968 adj=0.1762254659869745
- log loss base=0.44410692143800384 adj=0.5246329529780714

### I-3 Holm (α=0.05)

| test | p | rank | threshold | significant |
|---|---|---|---|---|
| `spread_clv_delta` | 0.0 | 1 | 0.005555555555555556 | True |
| `spread_ats_delta` | 0.0 | 2 | 0.00625 | True |
| `total_clv_delta` | 0.0 | 3 | 0.0071428571428571435 | True |
| `total_ats_delta` | 0.0 | 4 | 0.008333333333333333 | True |
| `total_logloss_delta` | 0.0 | 5 | 0.01 | True |
| `ml_clv_implied_prob_delta` | 0.0 | 6 | 0.0125 | True |
| `ml_ats_delta` | 0.0 | 7 | 0.016666666666666666 | True |
| `ml_logloss_delta` | 0.0 | 8 | 0.025 | True |
| `spread_logloss_delta` | 0.0034 | 9 | 0.05 | True |

### K-3 primary CI

spread_clv_delta obs=-0.06045751633986928 CI=[-0.0784313725490196, -0.042483660130718956] excludes_0=True p=0.0 blocks=34 seed=2708041115

### Reliability bins (K-2, 10 bins, counts)

**spread**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 68 | 0.03136283027639358 | 0.0 |  |
| 1 | 136 | 0.1457721700447549 | 0.0 |  |
| 2 | 68 | 0.27365323012631193 | 0.0 |  |
| 3 | 68 | 0.36612903556399967 | 0.0 |  |
| 4 | 68 | 0.46382608234895434 | 0.0 |  |
| 5 | 68 | 0.5670539752059206 | 0.0 |  |
| 6 | 68 | 0.6765643656130702 | 0.0 |  |
| 7 | 34 | 0.7939352929471261 | 0.0 |  |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 34 | 0.9233840890824001 | 0.0 |  |

**total**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 0 | None | None | bin empty; not a stub |
| 2 | 0 | None | None | bin empty; not a stub |
| 3 | 0 | None | None | bin empty; not a stub |
| 4 | 278 | 0.4003125703548006 | 1.0 |  |
| 5 | 0 | None | None | bin empty; not a stub |
| 6 | 334 | 0.6272928631256388 | 0.0 |  |
| 7 | 0 | None | None | bin empty; not a stub |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 0 | None | None | bin empty; not a stub |

**ml**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 68 | 0.05001895433626302 | 0.04411764705882353 |  |
| 1 | 68 | 0.14995804623715214 | 0.14705882352941177 |  |
| 2 | 68 | 0.24997314970004686 | 0.25 |  |
| 3 | 68 | 0.3499927779548031 | 0.35294117647058826 |  |
| 4 | 68 | 0.4499997084670482 | 0.45588235294117646 |  |
| 5 | 68 | 0.5500002915329518 | 0.5441176470588235 |  |
| 6 | 68 | 0.6500072220451969 | 0.6470588235294118 |  |
| 7 | 68 | 0.7500268502999532 | 0.75 |  |
| 8 | 34 | 0.8500419537628479 | 0.8529411764705882 |  |
| 9 | 34 | 0.949981045663737 | 0.9411764705882353 |  |

Baseline and adjusted used the **same** identical-close cohort. No arm-specific drop after scoring started.

## Cohort `synthetic_pass`

Known answer: 2 full seasons, n>=500, primary Holm-significant, CI excludes 0, K-4 passes → VALUE PROVEN on this fixture only. Not a product claim (I-5). Not the holdout.

- I-2: `MET` — n_nonzero_adjustment=612 by_season={2018: 306, 2019: 306} full_seasons=2
- I-4 decision: **VALUE PROVEN** (primary_holm=True, CI_excludes_0=True, k4=True)
- Product claim: False (null results reported as null; no product claim)
- Identical cohort n=612 ; paired both-CLV n=612
- Missing: incomplete=0 close=0 actual=0 baseline=0
- Missing by season: incomplete={} close={} actual={} baseline={}
- Universe by season: {2018: 306, 2019: 306}
- edge=0 drops: base=0 adj=0
- K-4: logloss_CI_hi=-0.08465366735389333 brier_CI_hi=-0.03472994036376619 slope=0.9990752469489775 pass=True []

### I-1 metrics (adj − base)

| metric | value |
|---|---|
| `spread_clv_delta` | -0.9117647058823529 |
| `spread_ats_delta` | -0.05065359477124183 |
| `spread_logloss_delta` | 0.020870914518413223 |
| `total_clv_delta` | -1.8169934640522876 |
| `total_ats_delta` | 0.4542483660130719 |
| `total_logloss_delta` | -0.13349339531796683 |
| `ml_clv_implied_prob_delta` | -0.05933419148587597 |
| `ml_ats_delta` | 0.12091503267973856 |
| `ml_logloss_delta` | -0.09099082098072642 |

### K-2 win-prob

- Brier base=0.21260333597641742 adj=0.1762254659869745
- log loss base=0.6156237739587979 adj=0.5246329529780714

### I-3 Holm (α=0.05)

| test | p | rank | threshold | significant |
|---|---|---|---|---|
| `spread_clv_delta` | 0.0 | 1 | 0.005555555555555556 | True |
| `spread_ats_delta` | 0.0 | 2 | 0.00625 | True |
| `total_clv_delta` | 0.0 | 3 | 0.0071428571428571435 | True |
| `total_ats_delta` | 0.0 | 4 | 0.008333333333333333 | True |
| `total_logloss_delta` | 0.0 | 5 | 0.01 | True |
| `ml_clv_implied_prob_delta` | 0.0 | 6 | 0.0125 | True |
| `ml_ats_delta` | 0.0 | 7 | 0.016666666666666666 | True |
| `ml_logloss_delta` | 0.0 | 8 | 0.025 | True |
| `spread_logloss_delta` | 0.0568 | 9 | 0.05 | False |

### K-3 primary CI

spread_clv_delta obs=-0.9117647058823529 CI=[-1.2352941176470589, -0.5882352941176471] excludes_0=True p=0.0 blocks=34 seed=2708041115

### Reliability bins (K-2, 10 bins, counts)

**spread**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 68 | 0.03136283027639358 | 0.0 |  |
| 1 | 136 | 0.1457721700447549 | 0.0 |  |
| 2 | 68 | 0.27365323012631193 | 0.0 |  |
| 3 | 68 | 0.36612903556399967 | 0.0 |  |
| 4 | 68 | 0.46382608234895434 | 0.0 |  |
| 5 | 68 | 0.5670539752059206 | 0.0 |  |
| 6 | 68 | 0.6765643656130702 | 0.0 |  |
| 7 | 34 | 0.7939352929471261 | 0.0 |  |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 34 | 0.9233840890824001 | 0.0 |  |

**total**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 0 | None | None | bin empty; not a stub |
| 2 | 0 | None | None | bin empty; not a stub |
| 3 | 334 | 0.3864380028488617 | 0.0 |  |
| 4 | 0 | None | None | bin empty; not a stub |
| 5 | 278 | 0.5287602255960249 | 1.0 |  |
| 6 | 0 | None | None | bin empty; not a stub |
| 7 | 0 | None | None | bin empty; not a stub |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 0 | None | None | bin empty; not a stub |

**ml**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 68 | 0.05001895433626302 | 0.04411764705882353 |  |
| 1 | 68 | 0.14995804623715214 | 0.14705882352941177 |  |
| 2 | 68 | 0.24997314970004686 | 0.25 |  |
| 3 | 68 | 0.3499927779548031 | 0.35294117647058826 |  |
| 4 | 68 | 0.4499997084670482 | 0.45588235294117646 |  |
| 5 | 68 | 0.5500002915329518 | 0.5441176470588235 |  |
| 6 | 68 | 0.6500072220451969 | 0.6470588235294118 |  |
| 7 | 68 | 0.7500268502999532 | 0.75 |  |
| 8 | 34 | 0.8500419537628479 | 0.8529411764705882 |  |
| 9 | 34 | 0.949981045663737 | 0.9411764705882353 |  |

Baseline and adjusted used the **same** identical-close cohort. No arm-specific drop after scoring started.

## Cohort `le2023`

Sealed le2023 export + OOS season<=2023. Close proxy is comparative research, not certified CLV. Not the sealed holdout.

- I-2: `MET` — n_nonzero_adjustment=2845 by_season={2013: 250, 2014: 254, 2015: 253, 2016: 256, 2017: 255, 2018: 256, 2019: 256, 2020: 254, 2021: 272, 2022: 268, 2023: 271} full_seasons=11
- I-4 decision: **NO CLAIM** (primary_holm=False, CI_excludes_0=False, k4=False)
- Product claim: False (null results reported as null; no product claim)
- Identical cohort n=2852 ; paired both-CLV n=2852
- Missing: incomplete=11 close=0 actual=0 baseline=0
- Missing by season: incomplete={2013: 2, 2014: 1, 2015: 1, 2017: 1, 2020: 2, 2022: 3, 2023: 1} close={} actual={} baseline={}
- Universe by season: {2013: 256, 2014: 256, 2015: 256, 2016: 256, 2017: 256, 2018: 256, 2019: 256, 2020: 256, 2021: 272, 2022: 271, 2023: 272}
- edge=0 drops: base=0 adj=0
- K-4: logloss_CI_hi=0.013748431943960889 brier_CI_hi=0.006767162022532177 slope=0.29283212349145965 pass=False ['logloss_CI_hi 0.013748431943960889 > 0.002', 'brier_CI_hi 0.006767162022532177 > 0.0005', 'slope 0.29283212349145965 outside [0.9, 1.1]']

### I-1 metrics (adj − base)

| metric | value |
|---|---|
| `spread_clv_delta` | 0.09431977559607294 |
| `spread_ats_delta` | -0.004908835904628331 |
| `spread_logloss_delta` | 0.008263327270575181 |
| `total_clv_delta` | 0.09291725105189341 |
| `total_ats_delta` | -0.00455820476858345 |
| `total_logloss_delta` | 0.008856415696099525 |
| `ml_clv_implied_prob_delta` | 0.0007436326253718226 |
| `ml_ats_delta` | -0.038569424964936885 |
| `ml_logloss_delta` | 0.01045045357435217 |

### K-2 win-prob

- Brier base=0.23823303019713066 adj=0.24338119186507587
- log loss base=0.6694230625485651 adj=0.6798735161229172

### I-3 Holm (α=0.05)

| test | p | rank | threshold | significant |
|---|---|---|---|---|
| `spread_logloss_delta` | 0.0 | 1 | 0.005555555555555556 | True |
| `total_logloss_delta` | 0.0 | 2 | 0.00625 | True |
| `ml_ats_delta` | 0.0 | 3 | 0.0071428571428571435 | True |
| `ml_logloss_delta` | 0.0 | 4 | 0.008333333333333333 | True |
| `spread_ats_delta` | 0.3092 | 5 | 0.01 | False |
| `spread_clv_delta` | 0.3612 | 6 | 0.0125 | False |
| `total_ats_delta` | 0.4624 | 7 | 0.016666666666666666 | False |
| `total_clv_delta` | 0.5704 | 8 | 0.025 | False |
| `ml_clv_implied_prob_delta` | 0.861 | 9 | 0.05 | False |

### K-3 primary CI

spread_clv_delta obs=0.09431977559607294 CI=[-0.10623344972143366, 0.2996526352698014] excludes_0=False p=0.3612 blocks=190 seed=2708041115

### Reliability bins (K-2, 10 bins, counts)

**spread**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 5 | 0.08719564865282678 | 0.6 |  |
| 1 | 63 | 0.17063276028543004 | 0.4603174603174603 |  |
| 2 | 281 | 0.25837429153683733 | 0.49110320284697506 |  |
| 3 | 585 | 0.35684867107718415 | 0.4376068376068376 |  |
| 4 | 728 | 0.4465395509681684 | 0.49175824175824173 |  |
| 5 | 543 | 0.5486652000098778 | 0.47513812154696133 |  |
| 6 | 472 | 0.6454504542719532 | 0.4766949152542373 |  |
| 7 | 136 | 0.742321099333335 | 0.5367647058823529 |  |
| 8 | 39 | 0.8310076951677099 | 0.38461538461538464 |  |
| 9 | 0 | None | None | bin empty; not a stub |

**total**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 7 | 0.16902345522577208 | 0.8571428571428571 |  |
| 2 | 107 | 0.2668121071716506 | 0.4766355140186916 |  |
| 3 | 321 | 0.3566042534103249 | 0.470404984423676 |  |
| 4 | 648 | 0.4541788991917224 | 0.47530864197530864 |  |
| 5 | 905 | 0.5480213550106497 | 0.47292817679558014 |  |
| 6 | 657 | 0.6427758811245555 | 0.4840182648401826 |  |
| 7 | 192 | 0.7386911222108753 | 0.4895833333333333 |  |
| 8 | 14 | 0.8332121910547986 | 0.35714285714285715 |  |
| 9 | 1 | 0.9091921607623754 | 0.0 |  |

**ml**
| bin | n | mean_p | mean_y | note |
|---|---|---|---|---|
| 0 | 0 | None | None | bin empty; not a stub |
| 1 | 0 | None | None | bin empty; not a stub |
| 2 | 6 | 0.2954454456839607 | 0.5 |  |
| 3 | 91 | 0.3654231118739446 | 0.43956043956043955 |  |
| 4 | 870 | 0.4620565592946832 | 0.48160919540229885 |  |
| 5 | 1478 | 0.5472975621226485 | 0.5615696887686062 |  |
| 6 | 379 | 0.6311757864475207 | 0.7071240105540897 |  |
| 7 | 28 | 0.722601279417105 | 0.5 |  |
| 8 | 0 | None | None | bin empty; not a stub |
| 9 | 0 | None | None | bin empty; not a stub |

Baseline and adjusted used the **same** identical-close cohort. No arm-specific drop after scoring started.

## Hard rules observed

- No 2024/2025/2026 rows scored.
- No CLEAR token created or accepted.
- No product or cert claim (I-5).
- Close proxy labeled comparative research, not certified CLV.
- v1/v2 holdout requests were not edited.
- Submission-readiness (5c4e6578): manifest + logs + metrics + gate table + provenance.
- Package checker (t4320u) verifies those and re-runs fixtures.

