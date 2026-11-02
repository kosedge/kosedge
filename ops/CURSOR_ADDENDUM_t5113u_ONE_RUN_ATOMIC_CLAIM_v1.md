# CURSOR ADDENDUM t5113u — atomic one-run claim before outcome join

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER t5113u · CoS ORDER t5113u · same #691 · parallel with t5112u
**No real EVAL. Defect fix only.**

## Defect @ 3f0675bd

`run_eval_score` called `run_paired_margin_eval` **before** `consume_one_run`. Consume was read-then-replace (not exclusive). Two processes could both verify BOUND and join outcomes. Sequential duplicate tests did not prove the one-look guard.

## Fix

1. After live-hash / preflight `verify_one_run`: **`claim_one_run`** creates `ONE_RUN.json.claim.{bind_id}` with `O_CREAT|O_EXCL` and sets status **IN_PROGRESS** — **before** any target-outcome join or metric computation.
2. Concurrent second caller: exclusive create fails → refuse; scoring body not entered.
3. Crash / injected failure after claim: status **FAILED**; claim file remains; automatic rerun refused.
4. Success writes a **separate** result receipt `ONE_RUN.json.result.{bind_id}.json`, then marks the bind record **CONSUMED**.

## Tests

```
cd services/model-service && PYTHONPATH=. python3.11 -m pytest \
  tests/test_nfl_t5113u_one_run_atomic_claim.py \
  tests/test_nfl_t5108u_impl_correction.py \
  tests/test_nfl_real_data_evaluator_t5107u.py -q
# 23 passed (3 new t5113u + prior one-run/eval)
```

- `test_concurrent_contenders_only_one_reaches_scoring_body` — two threads; `entered == 1`
- `test_injected_failure_after_claim_refuses_automatic_rerun` — FAILED + claim retained; second call refused
- `test_claim_file_is_exclusive_for_bind_id`

Prior sequential CONSUMED test retained.

## Tips

| Pin                     | Value                                               |
| ----------------------- | --------------------------------------------------- |
| PR                      | https://github.com/kosedge/kosedge/pull/691 (DRAFT) |
| Parent                  | `3f0675bddfdfbdc246a19e2530ec02f34eba66e1`          |
| This implementation tip | `0505da820912214365199bfbb935485cb5828e95`          |
| Design seal             | `e5bb682d…addd` (unchanged; not a forecast freeze)  |

## Remaining

No real EVAL until Alex verifies this claim fix **plus** complete 2020–23 inputs (t5112u freeze `f326a39a` / cohort `af129383`) **and** CoS one-run bind. CERT=0.

Coordination hard cutoff 20:00 UTC. No scope expand.
