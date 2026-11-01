# t5033u — Q2 strength adapter + one Appendix O look (DEV_RESEARCH)

**Label:** RETRO_FIT / DEV_RESEARCH · CERT=0 · NFL NO-GO · research-consumed only · DRAFT
**Do not merge · do not deploy · do not pub/bet · no CERT · no second look.**

Cite t5033u · fdf91ff5 · d7e0a6bc · 2db90f76 · 2b9f302e · 03a4dd90 CLOSED.
Guardrails `52c79ee6`. #684 ACCEPT `9982d42f` undisturbed.
t5035u guard-only follow-up: Alex RETURN `404a4ab2` · `d47934ca`.
`PROTOCOL_FREEZE` is not rewritten; rows are bound in
`artifacts/FREEZE_ADDENDUM.json` (`0d6a5e14…`). No second look.

## What this is

New research-tree offline **Layer-2** adapter (pattern `score_t4910u` @
`6ca03716` — sealed caller not edited). Generates 70 matching Q2 rows for
the frozen 2017 REG manifest and emits **NEW `research.q2s.*` fields only**:

`research.q2s.margin_mu_q2s = 0.5 * IF.margin_mu + 0.5 * q2_pm_new`

w=0.5 is a predeclared research candidate — **NOT** fitted or proven
optimum. No extra HFA. Baseline IF.margin_mu / total_mu / sigma / MC draws
stay unchanged. No candidate win/ATS/OU probabilities.

Then **one** Appendix O comparison on those 70 only. Original Q2 EVAL
`03a4dd90` remains CLOSED.

## Source gate (before any outcome scoring)

Exact frozen 70-game 2017 REG manifest + genuine sealed baseline
forecasts/results from t4910u control `SCORE_RESULTS.json` sha256
`2b9f302e097183ef275185a4edb100ab206565a087ca1ce78dbe8062524e877a`.

Copied read-only from draft #672
`data/ops/nfl-hist-diag-score-70-t4910u/` (ops-box path
`ops/nfl_enterprise_green_t4359u/nfl-hist-diag-score-70-t4910u/`).

`f_margin` = IF `forecast_margin`. `r_margin` = `realized_margin`.

#684 2013 REG W2 demo contains placeholder IF margins → mechanical
fixtures only. Never outcome scoring. Never a substitute for real forecasts.

## Pins (refuse-on-mismatch)

games `4fe1cdd7` · fit `70db070d` · FROZEN `aa2b47b3` / md `28c582a1` ·
as-of `cf514078` · score-only extract `50bda875` · SCORE_RESULTS `2b9f302e`

## Fit exclusion

Keep packet: DEV 2013–16 REG W2–17 only (`n_fit=960`). `HISTORY_ONLY_SEASONS = (2017,)`.
season_end_ratings stop at 2016. The 70 targets are 2017 REG W2–W6 and
were not in the `a_q2`/`b_q2` fit (`70db070d`).

If complete same-game real forecasts **or** fit exclusion cannot be
proven → refuse the comparison, preserve missing coverage, report the
exact blocker. No synthetic fallback. No silent subset.

## Isolation amend (narrow)

Amends #681 §4 + H6 for this single comparison only. See
`authority/AMEND_681_ISOLATION_H6.md`. No Layer 3. No sealed-writer rewrite.

## Reproduce

```bash
python3 research/q2s_adapter_t5033u/tests/test_q2s_adapter.py -v
python3 research/q2s_adapter_t5033u/emit_q2s_adapter.py
python3 research/q2s_adapter_t5033u/freeze_protocol.py
python3 research/q2s_adapter_t5033u/compare_appendix_o.py
```

Freeze **before** the comparison. One look. Stop.

## B2 (corrected)

Do **not** use the old antisymmetric venue-swap test.

- Reversing reporting coordinates for the **same** game flips the whole margin.
- Swapping teams/venue is a **different** event: keep the home intercept;
  Q2 `a+b*d` vs `a−b*d` sum to `2a`.
- Do not force an intercept-bearing forecast to be antisymmetric under a venue swap.
