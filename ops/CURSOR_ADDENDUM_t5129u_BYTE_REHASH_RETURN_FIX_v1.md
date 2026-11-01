# CURSOR ADDENDUM t5129u — BYTE REHASH RETURN-FIX

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: Alex RETURN **f5788f7c** · COS ORDER RETURN-FIX (sha8 in `ops/COS_ORDER_CURSOR_t5129u_BYTE_REHASH_RETURN_FIX.md`)
Parent tip `f4f6e311` / HEAD `2847ffc1`. Stays on #693. No EVAL EXEC. No claim.

## Preserve (unchanged)

| Artifact                           | sha256                                                                                       |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| First-case DEV_RESEARCH (CIN_CLE)  | file `8cb9a2a1…` · record `621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc` |
| DEV437 record                      | `0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637`                           |
| DEV437 file                        | `66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50`                           |
| `ONE_RUN.json`                     | `96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d`                           |
| `ONE_EXEC_RESULT_t5116u.json`      | `913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6`                           |
| `CURSOR_ONE_EXEC_RESULT_t5116u.md` | `be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3`                           |

R2-A coverage files **not** written. G5 / KO−60 / ≤24h / DK-FD **not** loosened.

## 1. ONE_RUN binds the R2 hash set

`bind_one_run(..., r2_runtime_bytes=)` stores `bind_id` + freeze / manifest / extract file-byte hashes on **ONE_RUN**. `bind_id` includes that set when present. `verify_one_run` checks live file hashes vs the ONE_RUN set **before claim**.

A side `R2_RUNTIME_BYTES` file can still be hashed, but it is not sufficient. Mutate freeze + fresh side rebind → **REFUSE** (`ONE_RUN r2_runtime_bytes mismatch`), loader = 0, no claim file, status remains BOUND.

## 2. Freeze file bytes ↔ `frozen.payload`

`frozen_from_forecast_file` derives the cohort from on-disk freeze bytes. Unrelated file + rebind refuses (`forecast file bytes do not match frozen.payload`) before claim / loader.

## 3. Manifest enumerates admitted extracts

Hashed manifest contents must list `admitted_extracts` (or `admitted_quote_extracts` / `quote_extracts`). Caller-supplied extract set must equal that set. Extra or missing files refuse before claim.

## 4. Pre-claim market completeness

When `score_body` is omitted (real EVAL scoring path), incomplete market for the eligible margin cohort refuses **before claim and before `outcome_loader`**. IF-only no longer claims then fails (look burn). Stubs still skip the contract.

## 5. Addendum path

This file and `ops/CURSOR_ADDENDUM_t5129u_R2_BYTE_REHASH_v1.md` stay under `ops/` for CoS seal. COS ORDER: `ops/COS_ORDER_CURSOR_t5129u_BYTE_REHASH_RETURN_FIX.md`.

## Tests

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
# 80 passed, 1 skipped
```

New: mutate+fresh rebind refuse; unrelated freeze+rebind refuse; caller extract set ≠ manifest; market incomplete / IF-only pre-claim (loader 0, BOUND).

## Hashes

| Artifact                | sha256 / tip                               |
| ----------------------- | ------------------------------------------ |
| Alex RETURN             | `f5788f7c`                                 |
| COS ORDER file          | sha8 `2a099402` (unstamped file `2a099402…`) |
| parent impl             | `f4f6e311e8af4d72163d71f389d6294e0e5d5f3b` |
| parent HEAD             | `2847ffc168fcbe10d36c9db5f6759bbfbafb65aa` |
| this implementation tip | *(stamped after commit)*                   |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC.
