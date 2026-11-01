# CURSOR ADDENDUM t5137u — full matched72 DEV comparison record

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5137u **574dde7f** · Cos ORDER **931260f0**
Parent #693 HEAD **0e8aa7f8** / market E2E impl **4c84cb55**
Stays on #693. No EVAL EXEC. No claim. No retune. No 94-DEV swap.

## Hypothesis (confirmed)

Persistence gap only. `run_market_e2e` already computed the full `market_contract`
(candidate / IF / market errors, paired diffs, frozen CIs, per-season). The
prior writer saved only market MAE/RMSE/bias on `MARKET_E2E_R2B_CONSUME.json`.
No other sealed full matched72 path existed. Writer/record path fixed by
**appending** a new DEV_RESEARCH file.

## Reporting reproduction (not independent confirmation)

The already-approved fixed DEV calculation was re-invoked **only** to persist
omitted output. Same freeze, schedule, quotes, consume, and sealed matched72
IDs. Market MAE/RMSE/bias reproduced the sealed parent receipt exactly.
This is **REPORTING_REPRODUCTION**, not a second look and not confirmation.

## Preserve (byte-immutable)

| Artifact | sha256 (unchanged) |
| -------- | ------------------ |
| `MARKET_E2E_R2B_CONSUME.json` (parent, market-only) | `380d530041892043902949ded7382a0f631261c3423565f36b094ccc814d93f0` |
| First-case DEV_RESEARCH (CIN_CLE) | file `8cb9a2a1…` · record `621f0f84…` |
| DEV437 | `66c3bde1…` |
| `ONE_RUN.json` | `96478f6b…` |
| `ONE_EXEC_RESULT_t5116u.json` | `91324259…` |
| `CURSOR_ONE_EXEC_RESULT_t5116u.md` | `be409f70…` |
| matched72 IDs `DEV_MATCHED_GAME_IDS.json` | `9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6` |
| ADMISSIBLE_QUOTES / manifest / consume | `75c0b14c…` / `bfcf8ff4…` / `09c3b86f…` |

Old **72** evidence was not rewritten. #694 normalized 94-DEV (`0a49afa3`) was
**not** substituted.

## DEV label

Matched call now passes `split="dev_reg"` (no inherited EVAL default).
Persisted record: `label=DEV_RESEARCH` · `metric_split=DEV` · `split=dev_reg`
· `cohort=matched72`.

## Appended record

`data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5137u_MATCHED72.json`

- exclusive create · n=72 · first `2020_02_CIN_CLE` · last `2021_18_DAL_PHI`
- `reporting=REPORTING_REPRODUCTION` · `reporting_class=DESCRIPTIVE_ONLY` (n=72 < 100)
- `eval=null` · `eval_invoked=false` · `one_run_claim=false` · CERT=0
- G5 `DATA_COVERAGE_BLOCKED` · not loosened
- `not_normalized_94=true`

### Contract numbers (matched72 only — reporting reproduction)

| Metric | Challenger | IF | Market |
| ------ | ---------- | -- | ------ |
| MAE | 10.180880751963878 | 10.820458179881213 | 9.38888888888889 |
| RMSE | 13.296695234977054 | 14.143476032703353 | 11.97791660144247 |
| bias | +1.6946080719830368 | +0.6027899379308674 | +0.5486111111111112 |

Paired mean signed absolute-loss diffs:

| Comparator | mean signed Δ | game-cluster CI95 (B=10000, seed 20261101) | week-cluster CI95 |
| ---------- | ------------- | ------------------------------------------ | ----------------- |
| vs IF | −0.639577427917335 | [−1.27866213, +0.00667501] INCONCLUSIVE | [−1.11044476, +0.20427831] INCONCLUSIVE |
| vs market | +0.7919918630749896 | [−0.10526357, +1.69657444] INCONCLUSIVE | [+0.18791050, +1.54716005] CI_EXCLUDES_ZERO |

Per-season:

| Season | n | MAE_C | MAE_IF | MAE_mkt | mean d_vs_IF | mean d_vs_mkt |
| ------ | - | ----- | ------ | ------- | ------------ | ------------- |
| 2020 | 35 | 10.77855614 | 11.24850614 | 10.20714286 | −0.46995000 | +0.57141328 |
| 2021 | 37 | 9.61551214 | 10.41554795 | 8.61486486 | −0.80003581 | +1.00064728 |

Market scalars match the sealed parent receipt. CI crossing zero = INCONCLUSIVE
(not retune permission). Not a claim.

## Tests

```
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_t5137u_matched72_dev_research.py \
  tests/test_nfl_t5119u_r2b_market_e2e.py \
  tests/test_nfl_t5129u_r2_byte_rehash.py \
  tests/test_nfl_t5125u_r2b2_dev_cohort.py \
  tests/test_nfl_t5119u_r2b_dev_seq.py \
  … t5116u / t5113u / t5108u / t5115u / real-data …
# 104 passed, 1 skipped
```

## Hashes

| Artifact | sha256 / tip |
| -------- | ------------ |
| OWNER CLEAR t5137u | `574dde7f` |
| Cos ORDER | `931260f0` |
| parent #693 HEAD | `0e8aa7f8` |
| market E2E impl | `4c84cb55` |
| matched72 record (payload) | `72a1f1f9ad1befa95b0cdb10588935da1e39fb857b06ee4f9a5778b1af1c3437` |
| matched72 record (file) | `88d63eb7f6b09e967fcf60122f525c2873072aaada93bb0dab3d8c3ff17fd9ea` |
| this implementation tip | `db08fdb77cc568d82131ab12d28b837c1c59ccdf` |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC.
