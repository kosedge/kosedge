# Isolation amend — #681 §4 + H6 (t5033u / fdf91ff5)

**RETRO_FIT / DEV_RESEARCH · CERT=0 · NFL NO-GO**

Narrow amend of [#681](https://github.com/kosedge/kosedge/pull/681) §4
research-field isolation and H6 **for this single Appendix O comparison
only**.

## Standing #681 §4 / H6 (still binding)

Sidecar / research fields must **not**:

- write `NflGameInputs.offense_index_*` / `defense_index_*`
- write L0 `off_eff_*` / `margin_mu` / `total_mu` / `sigma` / `market_blend`
- write `independent_fair.margin_mu` / `total_mu` / `sigma`
- blend Q2 into EPA
- shift MC draws

H6 (isolation hold): do not consume Q2 as a live forecast-margin write.

## What this amend allows (this package only)

A research-tree field `research.q2s.margin_mu_q2s` may be formed as

`0.5 * IF.margin_mu + 0.5 * q2_pm_new`

beside an **unchanged** sealed IF forecast. w=0.5 is a predeclared
research candidate — not fitted. No extra HFA.

## What this amend does not allow

- Overwriting baseline IF mus / sigma / draws
- Candidate win / ATS / OU probabilities from unchanged draws
- Layer 3 (`routes/nfl.py`, `tasks.py`, `NflGameInputs`)
- A second weight, a second look, merge, deploy, CERT lift
- Reopening Q2 EVAL `03a4dd90`
- Editing sealed `score_t4910u.py` or `emit_q2_asof_sidecar.py`
