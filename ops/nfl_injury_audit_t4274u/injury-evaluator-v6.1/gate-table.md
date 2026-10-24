# Gate table — a156459b verbatim + acceptance 54bc78ec operational reading

**SoT spec sha256:** `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`  
**Acceptance spec sha256:** `54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574`  
**Ruling (authoritative, this package):** `e7a0d737ab6116f40884115b667aa0abda671c29cdeaf7ac3ccf8c0940abb3c4`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v5.txt`  
**Prior readiness:** `1ef1f0a7ead7cb9397f7849785b6d3a0fa286526d1770f260c10062083afd083`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v4.txt`  
**Path 1 ruling:** `d18ebf22454073817d21b217b98cd9210a481369dbce7694929ac95114866d65`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_B3_PATH1_EXPORT_v1.txt`  
**Erratum:** `501e8a99dcb1a6553a3d8e40dc76918cc015705bcd336d0e50ac397a07662477`  
  `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_B3_PATH1_EXPORT_v1_ERRATUM_v1.txt`  
**Cited copy `0e0d54bc`:** NON-AUTHORITATIVE (paraphrase; kept, not deleted).  
**Prior ruling:** `88da5f42d918a9462da01ac01fd8260f7a0d9c2cad6a587492e5b9caf41cca6b`  
**Export pin:** on-disk `a38a55bb` (`46d2a565` is blob only)  
**Spec v2:** not used as SoT.  
**This table quotes s6/s7. It does not retune gates.**  
**Holdout STOPPED (t4315u `d6fca6f0`). No CLEAR.**

Line numbers are 1-based in the verified SoT spec.

---

## Verbatim blocks (s6 K, s7 I)

```
K-2  Metrics, base vs adjusted on the same games: Brier and log loss (win prob);
     cover reliability for spread and total (predicted cover prob vs actual);
     reliability diagram in 10 bins with counts.
K-3  CIs: block bootstrap by NFL week, 10,000 resamples, 95% percentile CI, paired.
K-4  Gate: adjusted must not be worse than base: upper 95% CI of (adj - base) log loss
     <= 0.002 and Brier <= 0.0005. Calibration slope of adjusted within [0.9, 1.1].
     Failing = layer stays off.
```

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

**Non-zero adjustment** (I-2 L138): `Δmargin ≠ 0` or `Δtotal ≠ 0`. Not `edge ≠ 0`.

**Full season (N-3):** weeks 1–17 if season < 2021; weeks 1–18 if season ≥ 2021.

**Close vs outcome (E-3 / I-1):** the I-1 “CLV” number is an **outcome-vs-close** score, labeled **close vs outcome**. It is not certified CLV and not price-vs-close CLV.

---

## Gate table

| Gate | Direction | Formula / procedure | Sample | Threshold | Spec citation |
|---|---|---|---|---|---|
| **I-1** | Report adj − base. Higher close-vs-outcome is better. | Same games, same as_of, vs close: close-vs-outcome points **and** implied-prob, ATS, log-loss delta. | Identical close-present set for K-2/K-4. ATS is **None** on no-pick (model==close or p==0.5); not a loss (B-1). | Metrics listed now. | L136–137 s7 |
| **I-2** | INCONCLUSIVE if shortfall. | Count **non-zero adjustment**. Full seasons as N-3. | Dry-run figure on le2023 folds; holdout ≥500 binds only at opening. | `n ≥ 500` and `≥ 2 full seasons`. | L138–139 s7 |
| **I-3** | 9 Holm tests. Primary stated now. | 3×3. Holm-Bonferroni α=0.05. Rejection = SIGNIFICANT. | Identical paired cohort. | Primary = mean close-vs-outcome delta (spread). | L140–141 s7 |
| **I-4** | VALUE PROVEN / NO CLAIM / INCONCLUSIVE. | I-2 MET **and** primary Holm-sig **and** primary CI **lo > 0** (favourable, E-2) **and** K-4. | I-2 + I-3/K-3. | VALUE PROVEN only if all hold. Else NO CLAIM. I-2 shortfall = INCONCLUSIVE. | L142–143 s7; acceptance I-4 operational |
| **I-5** | Disclosure. | Soft/null stay null. | All metrics. | No product claim. Fold labels: DRY RUN - NOT A RESULT. | L144–145 s7 |
| **K-2** | Report (feeds K-4). | Brier, log loss (win prob); cover reliability spread+total; 10 bins + counts. Same games both arms. | Close-present identical set (edge=0 kept). | No numeric cut. | L125–127 s6 |
| **K-3** | CI engine. | Week-block bootstrap, 10,000, 95% percentile, paired. Seed **20261023**, `numpy.default_rng`. | Week blocks. | Undefined resample ≠ 0.0 (E-5); any undefined → CI fail-closed. | L128 s6 |
| **K-4** | Layer-off. | UCI95(LL_adj−LL_base), UCI95(Brier_adj−Brier_base); slope b of logit(y)~logit(p_adj) (logistic MLE, E-6). | Same as K-2. | LL UCI ≤ 0.002, Brier UCI ≤ 0.0005, b ∈ [0.9,1.1]. Uncomputable = fail. | L129–131 s6 |

### I-3 nine tests

| # | Test id | Market | Metric |
|---|---|---|---|
| 1 | `spread_clv_delta` | spread | mean close-vs-outcome delta, points (**PRIMARY**) |
| 2 | `spread_ats_delta` | spread | ATS win-rate delta |
| 3 | `spread_logloss_delta` | spread | cover-prob log-loss delta |
| 4 | `total_clv_delta` | total | close-vs-outcome delta, points |
| 5 | `total_ats_delta` | total | over/under hit-rate delta |
| 6 | `total_logloss_delta` | total | over-prob log-loss delta |
| 7 | `ml_clv_implied_prob_delta` | moneyline | implied-prob close-vs-outcome (N-2): `(y_home − p_close) × sign(p_arm − p_close)` |
| 8 | `ml_ats_delta` | moneyline | pick-hit-rate delta (`p > 0.5`) |
| 9 | `ml_logloss_delta` | moneyline | win-prob log-loss delta |

### I-4 outcomes

| Outcome | When |
|---|---|
| **INCONCLUSIVE** | I-2 not met |
| **VALUE PROVEN** | I-2 MET and primary Holm-sig and **CI lo > 0** and K-4 |
| **NO CLAIM** | anything else |

---

## Close

Provider close = **nflverse REG `spread_line` / `total_line`**, converted to home-spread (package `inputs/nflverse_close_le2023.csv`, extracted from historical OOS `market_*` with 2024+ skipped before store). Book/consensus and timing **UNSPECIFIED**. Labeled:

**comparative research, not certified CLV** — metric name **close vs outcome**.

Holdout, if ever opened, will use this same nflverse source (E-9 declaration).

---

## N-1 sigma

fit_object `6a5490db` has **no sigma field**. Margin σ = **13.5** (C-10 default in `services/model-service/src/services/nfl_injury_null_contract.py` L339–341 / L410 at HEAD `8e2a15ac`). Totals σ = **14.0** (pre-registered in `inputs/sigma_preregistration.md`; totals tests only). T-5 unit test uses σ=13 as written. No √2 rescale.

**B-3:** `source_ts` / `as_of_ts` must ride from the sealed export through `join_fold`. If those fields are absent, stop and report; do not join close/outcome.

**B-4:** every path is package-relative. Missing input stops cleanly. No `/cursor/stores/self` or `/opt/cursor` fallbacks.

**C-2 (1ef1f0a7):** pin the 11 C-5 `game_id`s listed in `notes/c2-holdout-incomplete-row-rule.md` and `t_expected/T1_T10_EXPECTED.json` T-9.p2_c5. Require null deltas and null per-side timestamps on them. Holdout: count and pin incomplete `game_id`s from the holdout export **before** any outcome or close join. Do not pre-declare a 2024/25 count.

**C-3 (1ef1f0a7):** le2023 raw `date_modified` is zone-bearing `Z` on all 58653 rows (see `notes/c3-raw-report-time-format.md`). The 4 games with gap < 5 h are not excluded. Holdout: same format census before join; naive/zoneless → STOP, then correct the export or exclude recorded gap < 5 h by that pre-declared rule.
