# Gate table — IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt

**Spec sha256 (verified):** `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`  
**Spec SoT (Grok box):** `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt`  
**Store copy used on this VM:** `/cursor/stores/self/imv-inputs/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt`  
**Spec v2:** not used.  
**This table quotes s6/s7. It does not paraphrase, invert, or retune.**  
**Ryan t4315u / decision `d6fca6f0`:** holdout STOPPED. No CLEAR. 2024–25 is not opened. This table is for the evaluator dry-run only.  
**Ryan t4317u / decision `5c4e6578`:** submission-readiness (a)–(e) required before IMV.  
**t4320u:** `check_submission_package.py` is the reusable safeguard.

Line numbers are 1-based in the verified spec file.

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

**Non-zero adjustment** (I-2 L138): a game whose injury adjustment is non-zero (`Δmargin ≠ 0` or `Δtotal ≠ 0`). Not `edge ≠ 0` vs close.

---

## Gate table

| Gate | Direction (how it decides) | Formula / procedure | Sample | Threshold / rule | Spec citation |
|---|---|---|---|---|---|
| **I-1** | Report paired adj vs base. Does not itself PASS/FAIL. | Same games, same as_of, vs closing line: CLV (points **and** implied-prob), ATS win rate, log-loss delta. | Identical cohort: residual-complete + close present **before** either arm is scored; primary mean on rows where **both** CLVs are defined (`edge ≠ 0` both arms). | Metrics listed now; no post-hoc swap. | L136–137 s7 |
| **I-2** | INCONCLUSIVE (no claim) if shortfall; else sample is large enough to decide I-4. | Count games with a **non-zero adjustment**. Require **2 full seasons**. | `n_nonzero_adjustment` on the scored universe; seasons are full iff weeks 1–18 are present. | `n ≥ 500` **and** `≥ 2 full seasons`. Below → **INCONCLUSIVE (no claim)**. | L138–139 s7 |
| **I-3** | Family-wise significance on 9 tests. Primary stated now. | 3 markets × 3 metrics = 9 tests. Holm-Bonferroni, family α = 0.05. | Same identical paired cohort as I-1. | Primary endpoint = **mean CLV delta (spread)**. A Holm rejection of the **primary** is significance (not “any rejection → fail”). | L140–141 s7 |
| **I-4** | VALUE PROVEN / NO CLAIM / INCONCLUSIVE. | Conjunction: I-2 met **and** primary significant after Holm **and** primary 95% week-block-bootstrap CI excludes 0 **and** K-4 passes. | I-2 sample + I-3/K-3 on the paired cohort. | **VALUE PROVEN** only if all four hold. **Anything else = NO CLAIM.** I-2 shortfall = INCONCLUSIVE. Layer stays off unless VALUE PROVEN (and even then ELIGIBLE only; I-5). | L142–143 s7 |
| **I-5** | Disclosure. Soft/null cannot become a claim. | Report soft, borderline, or insignificant results as **null results**. | All reported metrics. | No product claim, marketing copy, or “improves accuracy” statement. | L144–145 s7 |
| **K-2** | Calibration report (feeds K-4). | Base vs adjusted on the **same** games: Brier and log loss (win prob); cover reliability for spread and total (predicted cover prob vs actual); reliability diagram in **10 bins** with counts. | Identical paired cohort. | Diagram: 10 bins + counts. No numeric pass cut in K-2 itself. | L125–127 s6 |
| **K-3** | CI / p-value engine for I-3, I-4, K-4. | Block bootstrap by **NFL week**, **10,000** resamples, **95%** percentile CI, **paired**. | Week blocks on the paired cohort. | `n_boot = 10000`. Seed pre-registered: `PINNED_SEED = 2708041115` (`int("a156459b", 16)`). Other seed voids the run. | L128 s6 |
| **K-4** | Layer-off gate. FAIL → layer stays off → I-4 cannot be VALUE PROVEN. | Upper 95% CI of **(adj − base)** log loss and Brier (week-block, paired). Calibration slope of **adjusted**. | Same paired cohort; win-prob Brier/log-loss. | Upper 95% CI (adj−base) log loss **≤ 0.002** **and** Brier **≤ 0.0005**. Slope of adjusted in **[0.9, 1.1]**. Failing = layer stays off. | L129–131 s6 |

### I-3 nine tests (3 × 3) — named, not invented as a different family

| # | Test id | Market | Metric |
|---|---|---|---|
| 1 | `spread_clv_delta` | spread | mean CLV delta, points (**PRIMARY**, I-3 L141) |
| 2 | `spread_ats_delta` | spread | ATS win-rate delta (adj − base) |
| 3 | `spread_logloss_delta` | spread | log-loss delta of predicted cover prob |
| 4 | `total_clv_delta` | total | mean CLV delta, points |
| 5 | `total_ats_delta` | total | over/under hit-rate delta |
| 6 | `total_logloss_delta` | total | log-loss delta of predicted over prob |
| 7 | `ml_clv_implied_prob_delta` | moneyline | CLV in implied-prob (adj − base) |
| 8 | `ml_ats_delta` | moneyline | pick-hit-rate delta (`p > 0.5`) |
| 9 | `ml_logloss_delta` | moneyline | log-loss delta of win prob |

### I-4 outcomes

| Outcome | When | Layer / claim |
|---|---|---|
| **INCONCLUSIVE** | I-2 not met | no claim; layer stays off |
| **VALUE PROVEN** | I-2 met **and** primary Holm-significant **and** primary 95% CI excludes 0 **and** K-4 passes | ELIGIBLE only; I-5 still bars product copy |
| **NO CLAIM** | anything else | null result (I-5); layer stays off |

---

## Close label (public proxy)

OOS `market_spread_home` / `market_total` used in the le2023 dry-run is a **public close proxy**. It is labeled:

**comparative research, not certified CLV**

No comparison to benchmark `5a653f63`. No product or cert claim.

---

## Hard rules for this evaluator

- 2024 / 2025 / 2026 rows are refused. Holdout is STOPPED (Ryan t4315u, `d6fca6f0`). No CLEAR.
- A CLEAR token must cite Ryan’s message id and the exact approved fingerprints. **No agent file can stand in.** This evaluator creates **no** token.
- v1 (`f74b3029`) and v2 (`0594a893` / `4f937c50`) stay as filed failures. This file does not edit them.
