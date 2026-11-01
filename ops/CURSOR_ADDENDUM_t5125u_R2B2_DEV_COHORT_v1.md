# CURSOR ADDENDUM t5125u R2-B2 — 437 DEV REG diagnostic + R2 loader-only runner

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5125u **ad000a52** under **9103dcff** · COS ORDER R2-B2 **0713a2b3**
CoS ACCEPT **61558ba9** = sequencing / single-example only — **not** reworked.
Stays on #693. No EVAL EXEC. No claim.

## Preserve

| Artifact                           | sha256 (unchanged)                                                                           |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| First-case DEV_RESEARCH (CIN_CLE)  | file `8cb9a2a1…` · record `621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc` |
| `ONE_RUN.json`                     | `96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d`                           |
| `ONE_EXEC_RESULT_t5116u.json`      | `913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6`                           |
| `CURSOR_ONE_EXEC_RESULT_t5116u.md` | `be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3`                           |

G5 / KO−60 / ≤24h / DK-FD **not** loosened.

## 1. R2 EVAL runner (new path; legacy `#693` score path untouched)

`run_eval_score_r2` (`r2_eval_runner.py`):

- requires `outcomes=None` **and** `outcome_loader`
- **refuses** preloaded scoring outcomes before HOLD/hash/claim
- loader call count = **0** on that refuse and on HOLD / hash / claim refuse
- success after claim = **1**

`#693` `run_eval_score` still accepts preloaded outcomes for old callers. R2 callers cannot use that path.

## 2. DEV REG 437 fixed-candidate diagnostic

Pin `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` · n=437 · WC 6 excluded.
Pinned freeze IF + fixed 0.5/0.5. IF mus **not** re-produced (N=4000, `seed_for` 201710/1000003, first-case seed 672662 disclosed). Bootstrap B=10000 seed 20261101 (game-cluster + week-cluster / `season_week`).

Metadata eligibility freeze → **then** one outcome_loader call (schedule scores). All 437 joined. First-case `err_c` still **−3.4880132517571516**.

Artifact: `data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5125u_R2B2_437.json`

- exclusive create · `one_run_claim=false` · `label=DEV_RESEARCH` · `CERT=0` · `eval=null`
- refuses dest = first-case file / t5116u SPENT names

### Contract numbers (n=437)

| Metric                      | Challenger    | IF            | Δ (C−IF)      |
| --------------------------- | ------------- | ------------- | ------------- |
| MAE                         | 11.0379610574 | 11.3637832400 | −0.3258221827 |
| RMSE                        | 14.0278937534 | 14.5320604179 | —             |
| bias (signed err)           | +1.1623607250 | +0.5192288264 | —             |
| mean signed-loss-diff vs IF | −0.3258221827 | —             | —             |

Per-season:

| Season | n   | MAE_C       | MAE_IF      | RMSE_C      | bias_C      | mean d_vs_IF |
| ------ | --- | ----------- | ----------- | ----------- | ----------- | ------------ |
| 2020   | 210 | 10.40958485 | 10.59784752 | 13.53639634 | +2.20751739 | −0.18826266  |
| 2021   | 227 | 11.61927825 | 12.07235814 | 14.46772232 | +0.19547570 | −0.45307989  |

Signed-loss-difference intervals (MEAN, B=10000, seed 20261101):

| Cluster     | point       | CI95                       | verdict          |
| ----------- | ----------- | -------------------------- | ---------------- |
| game        | −0.32582218 | [−0.55140004, −0.09892809] | CI_EXCLUDES_ZERO |
| season_week | −0.32582218 | [−0.54011612, −0.11581407] | CI_EXCLUDES_ZERO |

`reporting_class=REPORTABLE_NOT_AUTO_PASS` (n≥100). Not a claim. Not EVAL.

## 3. Market = NOT_READY

R2-A (`cursor/t5119u-r2a-owned-coverage-c2e1`, bc-7292a9b8) is still running. Workspace has inventory/addendum scripts only — **no** sealed verified quote extract/manifest. No invented market comparison. Market E2E prerequisite unmet.

## 4. Tests

```
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_t5125u_r2b2_dev_cohort.py \
  tests/test_nfl_t5119u_r2b_dev_seq.py \
  tests/test_nfl_t5116u_quote_hold_failclosed.py \
  tests/test_nfl_t5113u_one_run_atomic_claim.py \
  tests/test_nfl_t5108u_impl_correction.py \
  tests/test_nfl_real_data_evaluator_t5107u.py \
  tests/test_nfl_t5115u_cohort_identity.py -q
# 61 passed, 1 skipped
```

10 new t5125u tests (R2 refuse-preload + HOLD/hash/claim loader=0; 437 contract; first-case/t5116u hashes).

## Hashes

| Artifact                 | sha256 / tip                                                       |
| ------------------------ | ------------------------------------------------------------------ |
| OWNER CLEAR t5125u       | `ad000a52`                                                         |
| COS ORDER R2-B2          | `0713a2b3`                                                         |
| CoS ACCEPT (seq/example) | `61558ba9`                                                         |
| DEV REG 437              | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| first-case record        | `621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc` |
| first-case file          | `8cb9a2a1dbde5be9f27370622ab46934117b86e3e0597daf78374b9c5fe27a82` |
| 437 record_sha256        | `0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637` |
| 437 file                 | `66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50` |
| parent #693 tip          | `a676faaa` / impl `8204c77f`                                       |
| this implementation tip  | `f0013d62c321a5dc94fcc9c713decc6af8538465`                         |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC.
