# t5033u — research.q2s adapter rows (DEV_RESEARCH)

**RETRO_FIT / DEV_RESEARCH · CERT=0 · NFL NO-GO · do not merge/deploy/pub/bet.**

NEW `research.q2s.*` only. Baseline IF mus / sigma / MC draws unchanged.
w=0.5 is a predeclared research candidate — NOT fitted or proven optimum.

## Pins

- games `4fe1cdd7` (require `4fe1cdd7`)
- outcomes `50bda875` (require `50bda875`)
- fit `70db070d` (require `70db070d`)
- config `aa2b47b3` (require `aa2b47b3`)
- as-of `cf514078` (require `cf514078`)
- frozen md `28c582a1` (require `28c582a1`)
- SCORE_RESULTS `2b9f302e` (require `2b9f302e`)
- IF tip `6ca03716` (sealed caller; not edited)

## Fit exclusion

- ok: `True`
- 2017 is HISTORY_ONLY in the keep packet: as-of carry into 2018; never fit / never EVAL-scored. a_q2/b_q2 are DEV 2013–16 REG W2–17 OLS (n_fit=960) on fit object 70db070d.

## Counts

- history games: 1335
- emitted rows: 70
- missing: 0
- refused: False

## Isolation

No writes to IF.margin_mu / total_mu / sigma / MC draws / L0 /
NflGameInputs / Layer 3. No candidate win/ATS/OU probabilities.
#684 ACCEPT `9982d42f` undisturbed. Q2 EVAL `03a4dd90` CLOSED.
