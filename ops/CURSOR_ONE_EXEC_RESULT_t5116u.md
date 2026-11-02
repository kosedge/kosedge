# CURSOR ONE EXEC RESULT t5116u — FAILED (HOLD)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: CoS ONE EXEC t5116u · Alex GO **c122b108** · CLEAR 61906c87 · SUPERSEDES t5114u (never claimed)
**Same authorized look. Not a second look. No auto-rerun. No second attempt.**

## Gate

| Check                                                                 | Result                                                                              |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| #692 HEAD                                                             | `3013f111a7daa0b433e8adf92f18381f0b958e21` MATCH                                    |
| impl                                                                  | `a9668540c94e76fcf6f542097c0bf350c213b2a4` MATCH                                    |
| EVAL fac21ebe n=449                                                   | MATCH                                                                               |
| METRIC_COHORTS c301a091                                               | MATCH                                                                               |
| DEV REG 92b91585 n=437                                                | MATCH                                                                               |
| NON_REG_WILDCARD f81d381e n=6                                         | MATCH                                                                               |
| freeze 9e704b98 / forecast f326a39a / full af129383                   | MATCH (892 not metric)                                                              |
| quote 6a1c1b37 / design e5bb682d / games 4fe1cdd7 / outcomes 50bda875 | MATCH                                                                               |
| path                                                                  | `run_eval_score` only: refuse_pooled → refuse_eval_quote_and_hold → **HOLD refuse** |
| claim                                                                 | **not taken** (no `ONE_RUN.json.claim.*`)                                           |
| outcome join / MAE / bootstrap                                        | **not run**                                                                         |
| 892 scored as EVAL                                                    | **no**                                                                              |

## Status: FAILED

`ONE_RUN.json` **FAILED** bind_id `39909c61ce9429896bd20edd37259803cad0e11f1e2d3c3828ee04c9faab1830`.

Bound on EVAL cohort **fac21ebe** (not af129383/892). `refuse_eval_quote_and_hold` fired **before** `verify_one_run` / `claim_one_run` / outcome join:

`G5 30% per-season HOLD tripped — refuse scoring`

Quote-eligible margin cohort from freeze_eligible_cohorts on manifest **6a1c1b37** sources (JSONL 2022–23 + open_close CSV 2022–23; runner checked the pin, did not rehash quote bytes):

| Season | Split            | Declared PBP REG | Quote-eligible n | Excluded         | Rate       | HOLD    |
| ------ | ---------------- | ---------------- | ---------------- | ---------------- | ---------- | ------- |
| 2020   | DEV (not scored) | 256              | —                | 46 (16+30 recon) | 17.97%     | no      |
| 2021   | DEV (not scored) | 272              | —                | 45 (16+29 recon) | 16.54%     | no      |
| 2022   | EVAL             | 271              | **47**           | 224              | **82.66%** | **YES** |
| 2023   | EVAL             | 272              | **85**           | 187              | **68.75%** | **YES** |

Quote-eligible **132** / EVAL **449**. HOLD threshold 30% on declared PBP REG dens 256/272/271/272. Criteria not waived.

## Required report

| Item                                | n                           |
| ----------------------------------- | --------------------------- |
| EVAL 2022–23 REG (metric pin)       | **449** (221+228)           |
| Quote-eligible (margin)             | **132** (2022:47 + 2023:85) |
| DEV REG                             | **437** (210+227)           |
| NON_REG_WILDCARD                    | **6**                       |
| Partials (fail-closed, all seasons) | **119** (30+29+32+28)       |

No ΔMAE / bootstrap. No CONSUMED receipt.

## Notes-only manifest patch

`FROZEN_MANIFEST.json` `input_bindings.notes` only: stale “RECON MISSING” → **RECON_BINDINGS_2020_2023**. Design seal **e5bb682d** unchanged. Appended after the FAILED bind so spec hash at bind stayed `3c54b9a8…`.

## Hashes

| Artifact                         | sha256                                                             |
| -------------------------------- | ------------------------------------------------------------------ |
| EVAL cohort                      | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| DEV REG                          | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| NON_REG_WILDCARD                 | `f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722` |
| freeze file                      | `9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732` |
| quote manifest                   | `6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984` |
| design seal                      | `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd` |
| ONE_RUN.json                     | `96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d` |
| ONE_EXEC_RESULT json             | `913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6` |
| bind_id                          | `39909c61ce9429896bd20edd37259803cad0e11f1e2d3c3828ee04c9faab1830` |
| Alex GO                          | `c122b1088a404db550ae570ccf0c2099e084d900233bd5d317b84990288eef3b` |
| EVAL-only forecast_sha256 (bind) | `989b85c6150bdd84b1a84c200e4f9d83b5e7081c094063405a6ae46de94b8e1a` |
| this implementation tip          | `f10abd948c1d7758e6b8f5f603e65f5b321ae648`                         |

CERT=0 · DRAFT≠merge · no merge · failure≠second look.
