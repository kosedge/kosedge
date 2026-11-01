# CURSOR ADDENDUM t5119u R2-B — market join E2E (consume R2-A)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: Cos ACCEPT **770f72da** · Cos ORDER market E2E **e7330717**
R2-A SEALED #694 tip **3821941d758feb7ba05e680da6ecec283291dd2a**
`R2B_CONSUME.market_e2e` = **READY_FOR_R2B_DEV_E2E**
Stays on #693. RETURN-FIX tip `a957745a` / HEAD `7368be5c` not rewritten. No EVAL EXEC. No claim.

## Consume only

Sealed artifacts copied unchanged from #694 (hashes MATCH `ARTIFACT_SHA256.json`):

| File                     | sha256           |
| ------------------------ | ---------------- |
| `R2B_CONSUME.json`       | `09c3b86f…`      |
| `ADMISSIBLE_QUOTES.jsonl`| `75c0b14c…` n=1475 |
| `COVERAGE_MANIFEST.json` | `bfcf8ff4…`      |

R2-A coverage directory was **not** rewritten after consume. G5 / KO−60 / ≤24h / DK-FD **not** loosened. 480 conflicts remain refused.

## Market join E2E (no EVAL)

`run_market_e2e` joins sealed admissible spreads onto the eligible cohort (`home_margin = −spread_home`). `outcomes=None` + loader only. Fail-closed on missing consume / pin mismatch / conflict fingerprint / non-DK-FD / age >24h. **Does not** call `run_eval_score` / `run_eval_score_r2`.

Receipt: `data/ops/nfl-forecast-builder-t5107u/MARKET_E2E_R2B_CONSUME.json`

| Cohort                         | eligible | joined | missing | bind_ready |
| ------------------------------ | -------- | ------ | ------- | ---------- |
| EVAL `fac21ebe`                | 449      | 95     | 354     | **false**  |
| DEV REG `92b91585`             | 437      | 72     | 365     | **false**  |
| DEV matched subset (R2-A list) | 72       | 72     | 0       | **true**   |

First-case `2020_02_CIN_CLE` is in the DEV matched 72 and received a sealed `market_margin`.

Joined DEV-matched 72 (loader after join, not EVAL): MAE_market 9.388889 · RMSE_market 11.977917 · bias_market +0.548611. Bootstrap B=10000 seed 20261101 present on that subset. Full EVAL result contract is **not** complete on 449 (missing 354) — DEV437 does not complete it either.

## READY for bind?

**EVAL bind: NO.** Eligible 449 is incomplete (95/449). Claiming EVAL bind would look-burn.

**DEV matched 72: YES** for a DEV_RESEARCH market-side bind on that subset only. Not an EVAL look.

## Preserve (unchanged)

First-case `8cb9a2a1` / `621f0f84` · DEV437 `66c3bde1` / `0550ef9b` · t5116u FAILED `96478f6b` / `91324259` / `be409f70`.

## Tests

```
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_t5119u_r2b_market_e2e.py \
  tests/test_nfl_t5129u_r2_byte_rehash.py \
  tests/test_nfl_t5125u_r2b2_dev_cohort.py \
  tests/test_nfl_t5119u_r2b_dev_seq.py \
  … t5116u / t5113u / t5108u / t5115u / real-data …
# 92 passed, 1 skipped
```

## Hashes

| Artifact                | sha256 / tip                               |
| ----------------------- | ------------------------------------------ |
| Cos ACCEPT              | `770f72da`                                 |
| Cos ORDER market E2E    | `e7330717`                                 |
| R2-A sealed tip         | `3821941d758feb7ba05e680da6ecec283291dd2a` |
| RETURN-FIX parent       | `a957745a` / HEAD `7368be5c`               |
| this implementation tip | `4c84cb550db64968b7213f43442be64275cf5c75` |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC.
