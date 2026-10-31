# VERDICT_ENG — t4915u Lane S

**FAILS_TO_SHOW**

Label: DEV_RESEARCH / RETRO_FIT exploratory. CERT=0. NFL NO-GO.
Not a predictive PASS. Not a betting PASS. Not CERT. Alex RO before any OWNER interpretation.

## Rationale (short)

On the sealed 70, every frozen signal’s Spearman and Pearson vs `realized_margin` has a bootstrap 95% CI that includes 0. Every OLS slope CI includes 0. Every Wilson SU interval that exists includes 50%. W-L signed diffs (`wl_diff`, `wl_index_off_diff`, `wl_index_net`) point the **wrong** way (ρ ≈ −0.13). EPA/success nets are near zero (RETRO_FIT / A1). `n_complete=70` / `n_ties=0` / no MISSING — this is not a missing-data artifact.

CIs are wide (typical Spearman half-width ~0.25). This EXEC does **not** prove zero information. It fails to show useful discrimination on the accepted, already-examined sample.

WEEK_SUBSET_AUDIT: no signed signal is week-stable. `wl_home_wpct` W2 vs W6 CIs exclude 0 in **opposite** directions. Other “concentration” flags are LOO noise around a null overall.

Association-to-IF is strong for W-L diffs (ρ ≈ 0.96). That says IF tracks the W-L index, not that the index tracks outcomes.

## Recommended next bounded experiment

**Further signal research — not Lane E.**

Do not open a Phase 2 Lane E paper CLEAR card from this EXEC (signals were not shown useful). Do not implement ablations, do not retune IF, do not touch tip `02197f58` / SCORE_RESULTS `2b9f302e`.

If CoS later wants more power, that is a **new OWNER ACCEPT** for a pre-registered larger already-owned historical window (not this 70 re-fit; not 2024–25; still RETRO_FIT / DEV_RESEARCH for EPA). Until then: stop Lane S on this sample.
