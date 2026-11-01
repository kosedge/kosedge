# CURSOR ADDENDUM t5119u R2-B — DEV numerical E2E + sequencing fix

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR **9103dcff** · COS ORDER R2-B · Alex t5116u PASS_RO **09fa4cc1**
NEW isolated DRAFT branch/PR. **Not a t5116u rerun. No EVAL EXEC. No claim.**

## Preserve (t5116u FAILED look SPENT)

Do not reset, retry, re-bind, or overwrite:

| Artifact                           | sha256 (MATCH, unchanged)                                          |
| ---------------------------------- | ------------------------------------------------------------------ |
| `ONE_RUN.json`                     | `96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d` |
| `ONE_EXEC_RESULT_t5116u.json`      | `913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6` |
| `CURSOR_ONE_EXEC_RESULT_t5116u.md` | `be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3` |

G5 30% HOLD, KO−60, ≤24h, DK/FD, and time/book rules were **not** loosened.

## 1. t5116u exposure (Alex notes, non-violation)

Alex PASS_RO 09fa4cc1 item: `load_outcomes` read 2022–23 EVAL scores into memory **before** the G5 HOLD gate. They were not joined, not printed, and produced no metrics. No scored look occurred.

That is a **source READ vs JOIN/metrics** sequencing hole: the target scoring-outcome loader ran on a path that then refused HOLD. R2 fixes the path. It does not reopen the spent look.

## 2. Sequencing fix (EVAL `run_eval_score`)

`outcome_loader` is the target JOIN handle. It is invoked **only after** HOLD + forecast/cohort re-hash + exclusive claim.

| Refuse                         | Loader call count                  |
| ------------------------------ | ---------------------------------- |
| G5 HOLD trip                   | **0**                              |
| forecast/cohort hash mismatch  | **0**                              |
| claim / IN_PROGRESS / second   | **0**                              |
| both preload and loader passed | **0** (caller error; no gate skip) |
| authorized success after claim | **1**                              |

Concurrent EVAL: winner loader count 1; loser 0. Preloaded `outcomes` remains back-compat after the same gates; it is the t5116u exposure and is not a reason to skip them.

New module: `services/model-service/src/services/nfl_t5107u/outcome_gate.py`.

## 3. DEV REG 437 numerical E2E (one `DEV_RESEARCH` record)

Pins (unchanged freeze body `f326a39a`):

| Pin              | n   | sha256                                                             |
| ---------------- | --- | ------------------------------------------------------------------ |
| DEV REG          | 437 | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| NON_REG_WILDCARD | 6   | `f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722` |

After metadata eligibility freeze (identity / kickoff TZ / pinned margins; **no** outcomes): first eligible id in DEV REG pin order = **`2020_02_CIN_CLE`**. WC 6 cannot be selected.

Hand-checkable (input → pinned IF + fixed 0.5/0.5 → market → error):

```
game     2020_02_CIN_CLE   home CLE  away CIN  kickoff 2020-09-18T00:20:00Z
m_if     0.07714026611934685   (RECONSTRUCTED_IF_6ca03716, freeze pin)
m_q2     2.94683323036635
m_c      0.5*m_if + 0.5*m_q2 = 1.5119867482428484   (match; no fit/search)
actual   35 − 30 = 5
err_c    1.5119867482428484 − 5 = −3.4880132517571516
err_if   0.07714026611934685 − 5 = −4.922859733880653
L_c      3.4880132517571516
L_if     4.922859733880653
d_vs_if  −1.4348464821235014
market   MISSING   reason=no_admissible_quotes_supplied
```

R2-A coverage manifest was **not ready** this window (parallel agent; no pins in-repo). Existing admissible quotes only; KosEdgeData unmounted on this box. Market labeled **MISSING** honestly. G5 / book / time rules unchanged.

Record: `data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json`

- label `DEV_RESEARCH` · `eval=null` · `one_run_claim=false` · `CERT=0`
- exclusive create; refuses dest names `ONE_RUN.json` / `ONE_EXEC_RESULT_t5116u.json`
- target join phase: `AFTER_METADATA_ELIGIBILITY_AND_PICK`

## 4. Output contract + tests (before any scale-up)

Required keys in `OUTPUT_CONTRACT` (`dev_research.py`). Incomplete records refuse. One game only. No scale-up.

```
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_t5119u_r2b_dev_seq.py \
  tests/test_nfl_t5116u_quote_hold_failclosed.py \
  tests/test_nfl_t5113u_one_run_atomic_claim.py \
  tests/test_nfl_t5108u_impl_correction.py \
  tests/test_nfl_real_data_evaluator_t5107u.py \
  tests/test_nfl_t5115u_cohort_identity.py -q
# 51 passed, 1 skipped
```

- Loader-call-count = 0 on HOLD / hash / claim refuse
- DEV first-eligible + WC excluded
- Synthetic missing-market and joined-market arithmetic
- Eligibility refuse → 0 target reads
- Exclusive DEV_RESEARCH write + two-thread concurrency (one winner)
- Spent t5116u hashes MATCH
- Real freeze pin 437/`92b91585` → `2020_02_CIN_CLE`

## 5. Not done (by order)

- No EVAL EXEC. No CoS claim. No second look on t5116u.
- No G5 waiver. No 2024–26. No Stage C. No invented ATS/OU probabilities.
- No candidate selection / weight search / extra HFA / market blend.
- R2-A quote pins not coordinated (coverage not ready).

## Hashes

| Artifact                      | sha256 / tip                                                       |
| ----------------------------- | ------------------------------------------------------------------ |
| OWNER CLEAR                   | `9103dcff`                                                         |
| COS ORDER R2-B                | this order                                                         |
| Alex PASS_RO                  | `09fa4cc1`                                                         |
| EVAL 449 (untouched)          | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| DEV REG 437                   | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| NON_REG_WILDCARD 6            | `f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722` |
| freeze file                   | `9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732` |
| quote manifest (not loosened) | `6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984` |
| ONE_RUN.json (SPENT)          | `96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d` |
| ONE_EXEC_RESULT json (SPENT)  | `913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6` |
| DEV_RESEARCH record_sha256    | `621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc` |
| DEV_RESEARCH file             | `8cb9a2a1dbde5be9f27370622ab46934117b86e3e0597daf78374b9c5fe27a82` |
| parent t5116u HEAD            | `61436fdb98fdbd4908a9af52563a2656677e2902`                         |
| this implementation tip       | _pending commit_                                                   |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC.
