# CURSOR ADDENDUM t5129u — R2 runtime byte rehash + inherited EVAL result contract

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5129u **31131644** · COS ORDER **c5c27625**
Ryan independent recompute DEV437 @ `6c54d729` — numbers **MATCH**. No retune.
Alex re-verify caller ORDER **15347bbd**. Stays on #693. No EVAL EXEC. No claim.

## Preserve

| Artifact                           | sha256 (unchanged)                                                                           |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| First-case DEV_RESEARCH (CIN_CLE)  | file `8cb9a2a1…` · record `621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc` |
| DEV437 record                      | `0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637`                           |
| DEV437 file                        | `66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50`                           |
| `ONE_RUN.json`                     | `96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d`                           |
| `ONE_EXEC_RESULT_t5116u.json`      | `913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6`                           |
| `CURSOR_ONE_EXEC_RESULT_t5116u.md` | `be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3`                           |

G5 / KO−60 / ≤24h / DK-FD **not** loosened. R2-A coverage files **not** written.

DEV437 limitations preserved: bias / per-season / `DEV_RESEARCH` only; market **NOT_READY**.

## 1. Runtime byte rehash (`r2_byte_rehash.py` / `run_eval_score_r2`)

In-memory `FrozenCohort.forecast_sha256` (re-serialize) and the quote-manifest **pin string** (`6a1c1b37…`) are insufficient.

R2 EVAL now requires, **before claim and before `outcome_loader`**:

1. SHA-256 of the frozen forecast **file** bytes
2. SHA-256 of the quote **manifest** file bytes
3. SHA-256 of **each** admitted quote extract file bytes
4. Exclusive bind of those hashes into a **new** run record (`bind_r2_runtime_bytes`, `O_CREAT\|O_EXCL`)

Refuse:

- missing forecast file / manifest file / empty extract list
- missing bind dest (no default onto `ONE_RUN` / first-case / DEV437 / R2-A)
- any mutated freeze / manifest / extract byte vs the bind
- dest name or resolved path in the preserved / R2-A set

`run_eval_score_r2` still: `outcomes=None` + `outcome_loader` only; preloaded refused first. Loader count = **0** on preload / byte-mutation / missing-extract refuse (no claim file). Success attaches `r2_runtime_bytes`.

## 2. Inherited EVAL result contract (schema/tests; no live EVAL)

`eval_result_contract.py` + `run_paired_margin_eval` now emit vs **both IF and market**:

- MAE / RMSE / bias
- `n_by_season` + per-season tables (same metrics + signed-diff means)
- game-cluster **and** season-week-cluster CIs on signed paired loss diffs (`B=10000`, seed `20261101`)

When `score_body` is omitted, `run_eval_score_r2` wraps `run_paired_margin_eval` and **applies** the contract (IF-only fails after loader; stub `score_body` skips). DEV437 is IF-only + market `NOT_READY` and **does not** complete this contract — tested.

## 3. Tests

```
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_t5129u_r2_byte_rehash.py \
  tests/test_nfl_t5125u_r2b2_dev_cohort.py \
  tests/test_nfl_t5119u_r2b_dev_seq.py \
  tests/test_nfl_t5116u_quote_hold_failclosed.py \
  tests/test_nfl_t5113u_one_run_atomic_claim.py \
  tests/test_nfl_t5108u_impl_correction.py \
  tests/test_nfl_real_data_evaluator_t5107u.py \
  tests/test_nfl_t5115u_cohort_identity.py -q
# 76 passed, 1 skipped
```

t5129u: freeze/manifest/one-extract mutation refuse (loader=0, no claim); empty extracts refuse; IF-only contract fail vs IF+market pass; DEV437 fails EVAL contract; preserved hashes + no R2-A files.

t5125u R2 runner tests now bind tmp freeze/manifest/extract so byte verify precedes HOLD/hash/claim.

## Hashes

| Artifact                 | sha256 / tip                                                       |
| ------------------------ | ------------------------------------------------------------------ |
| OWNER CLEAR t5129u       | `31131644`                                                         |
| COS ORDER                | `c5c27625`                                                         |
| Alex re-verify ORDER     | `15347bbd`                                                         |
| Ryan MATCH DEV437 @      | `6c54d729`                                                         |
| DEV REG 437              | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| first-case record        | `621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc` |
| 437 record_sha256        | `0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637` |
| parent #693 tip          | `6c54d729` / impl `f0013d62`                                       |
| this implementation tip  | *(stamped after commit)*                                           |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC.
