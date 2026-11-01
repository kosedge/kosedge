# CURSOR ADDENDUM t5116u — narrow RETURN fixes

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: Alex RETURN **ee5af10b** · CoS ORDER t5116u · OWNER t5115u · #692
**Not a second look. Not a new experiment. No claim. No score. No EXEC.**

## 1. GitHub DRAFT restored

`gh pr ready 692 --undo` → **isDraft=true**.  
https://github.com/kosedge/kosedge/pull/692

ManagePullRequest cannot convert GitHub-source-of-truth PRs back to draft; GitHub CLI did.

## 2. Prettier

`npx prettier@3.3.3 --write` then `--check` **green** on:

- `data/ops/nfl-forecast-builder-t5107u/METRIC_COHORTS_t5115u.json`
- `data/ops/nfl-forecast-builder-t5107u/IDENTITY_RESOLUTION_2020_t5115u.json`
- `ops/CURSOR_ADDENDUM_t5115u_COHORT_IDENTITY_RECON_v1.md`
- `ops/CURSOR_ADDENDUM_t5116u_NARROW_RETURN_FIXES_v1.md`

## 3. Appended cohort (freeze body untouched)

`FORECAST_FREEZE_t5112u.json` still file `9e704b98…` / forecast **f326a39a…** / full cohort **af129383…**. Not rewritten.

| Pin                             | n                 | sha256                                                             |
| ------------------------------- | ----------------- | ------------------------------------------------------------------ |
| EVAL (unchanged)                | **449** (221+228) | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| DEV retain (all freeze DEV)     | 443               | `f240fde23025d7584a5f8031ec1e0e74f902be1100ce1630aca4f2f20ed326b0` |
| **DEV REG** (appended)          | **437** (210+227) | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| **NON_REG_WILDCARD** (appended) | **6**             | `f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722` |

The six `2020_18_*` rows stay in the freeze with whatever `season_type` the freeze already has. The appended cohort file labels them **NON_REG_WILDCARD** / POST Wild Card. They are not EVAL and not in declared 2020 REG 256.

File: `data/ops/nfl-forecast-builder-t5107u/METRIC_COHORTS_t5115u.json`

## 4. Fail-closed before outcome join (and before claim)

`run_eval_score` now calls `refuse_eval_quote_and_hold` after the pooled-892 refuse and **before** `verify_one_run` / `claim_one_run` / outcome join. When the freeze includes EVAL seasons (2022–23):

- `eligible_cohorts` required
- `sealed_after_eligibility_before_outcome_join` required (from `freeze_eligible_cohorts`)
- `quote_manifest_sha256` must be **6a1c1b37…** (frozen quote manifest)
- margin game_ids must be a subset of that freeze’s EVAL pin (449 on the sealed freeze)
- `g5_hold` required; declared_n must be owned PBP REG **256/272/271/272**; any season `hold=true` refuses

Not optional flags. Tests in `tests/test_nfl_t5116u_quote_hold_failclosed.py`: missing quote pin, unsealed eligible, HOLD trip, wrong declared n, id outside EVAL — all refuse with status still BOUND and no claim file.

Quote join / metrics / EXEC were **not** run.

## 5. EXEC

`ONE_RUN.json` still absent. t5114u remains STOPPED_UNCLAIMED. Do not re-enter EXEC until Alex re-verify + CoS re-bind on **fac21ebe** (not 892). Same authorized look.

## Hashes

| Artifact            | sha256                                                             |
| ------------------- | ------------------------------------------------------------------ |
| Alex RETURN tip     | `ee5af10b7a8e0333a40f57a674882756b2549bdcfc6ff13ba6f64055a160c829` |
| parent #692 HEAD    | `2a4e22174b11c44f430cb80a9ee3f08f86beaaa9`                         |
| EVAL 449            | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| DEV REG 437         | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| NON_REG_WILDCARD 6  | `f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722` |
| freeze file         | `9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732` |
| quote manifest      | `6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984` |
| METRIC_COHORTS file | `c301a09189f332a2017fd082408962dbb5a97a57c17c362b4fa012f382090923` |

CERT=0 · DRAFT≠merge · no merge/send.
