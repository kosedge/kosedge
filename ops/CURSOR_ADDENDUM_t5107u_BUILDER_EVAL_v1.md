# CURSOR ADDENDUM t5107u — forecast builder + evaluator scaffolding v1

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER AMEND+CLEAR t5107u G1–G7 · CoS order under d7e0a6bc

Place a copy at `ops/CURSOR_ADDENDUM_t5107u_BUILDER_EVAL_v1.md` (this branch). `/workspace/ops` is not mounted on this worker.

## Preserve

Prior ACCEPT history stands. This addendum is a new tip only.

| Pin                            | Value                                                              |
| ------------------------------ | ------------------------------------------------------------------ |
| CoS ACCEPT                     | `e68a11cb`                                                         |
| PASS_RO                        | `e78176c3`                                                         |
| t5105u addendum                | `c8075622`                                                         |
| CLEAR                          | `4f3b9666` / `02ca8367`                                            |
| Paper tip                      | `7139f8d9eed71b47eabf8827c0593932a38fea9a36686c66df3f6311282628c7` |
| Prior #689 draft head (t5105u) | `f33637db75def870bc9b9ca84a73ce754b21cdae`                         |
| Prior #690 draft head (t5105u) | `cc594b6fb09b8fdb5368e13be72a263e88920e4c`                         |

PRs remain DRAFT. No merge / deploy / paid Odds. No EXEC scoring. Paper controls stay immutable.

## Track A — first artifact

**First artifact:** sealed `data/ops/nfl-forecast-builder-t5107u/FROZEN_MANIFEST.json`

- path: `data/ops/nfl-forecast-builder-t5107u/FROZEN_MANIFEST.json`
- sha256 (body, excluding the self-hash field): `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd`
- sealed design / input-source / fit-policy **before** EVAL sequential generation
- `eval_generation`: NOT_RUN
- `exec_scoring`: REFUSED_PENDING_ALEX_PREFLIGHT_AND_COS_BIND

Builder / evaluator (new DRAFT PR, unmerged):

| Item                         | Path                                                           |
| ---------------------------- | -------------------------------------------------------------- |
| Q2 transfer + ridge as-of    | `services/model-service/src/services/nfl_t5107u/q2.py`         |
| IF archived vs reconstructed | `services/model-service/src/services/nfl_t5107u/if_control.py` |
| Forecast builder             | `services/model-service/src/services/nfl_t5107u/builder.py`    |
| Evaluator scaffolding        | `services/model-service/src/services/nfl_t5107u/evaluator.py`  |
| Manifest seal                | `services/model-service/src/services/nfl_t5107u/manifest.py`   |
| CLI                          | `scripts/nfl/run_nfl_forecast_builder_t5107u.py`               |

Reuse, not rewrite: Q2 intercept/slope + as-of from `8155fd194` / `FROZEN_CONFIG_Q2PB_t5009u`; IF consume labels from `19c6a4607` / `6ca03716`. t5105u reader TZ contract and harness p-bind are imported, not redone.

### Fit policy (G1)

Q2 coefficients **transfer**. Frozen DEV OLS was trained on REG 2013–2016 only (`training_end=2016 ≤ 2021`). No 2020–21 intercept/slope refit was performed or authorized.

- `a_q2 = 2.5637441292077354`
- `b_q2 = 1.660624056183471`
- `λ = 20`, `r = 0.5`
- `mC = 0.5*mIF + 0.5*mQ2` (extra HFA / market blend / weight search refused)
- parameter label: `FROZEN_Q2PB_DEV_2013_2016_TRANSFER` (`original_frozen`)

### Tests (local `python3.11 -m pytest`)

```
cd services/model-service && PYTHONPATH=. python3.11 -m pytest \
  tests/test_nfl_odds_reader.py \
  tests/test_nfl_odds_comparison_harness.py \
  tests/test_nfl_forecast_builder_t5107u.py \
  tests/test_nfl_real_data_evaluator_t5107u.py -q
...............................................  47 passed
```

- Prior reader+harness: **26/26** (unchanged)
- New builder: **13**
- New evaluator: **8**
- Combined: **47/47**

Covered: Q2 transfer proof + refit refuse; causal prior-game as-of; target-row leak refuse; archived vs reconstructed IF labels; silent IF drop refuse; IF-blocked challenger; EVAL generation gate; 2024–25 / Stage C refuse; naive TZ refuse; freeze-before-outcome-join; EXEC score refuse; hash-mismatch refuse; KO−60 + ≤24h + DK/FD; multiplicative de-vig; p-bind unbound refuse; bootstrap B=10000 seed 20261101; n<100 DESCRIPTIVE_ONLY; 30% per-season HOLD; invented ATS/OU refuse.

## Track B — Prettier / formatting CI

Failed check on prior heads (only this check failed; Vercel / Railway succeeded — report separately):

| PR                                                  | Prior head | Failed check      | Failed step                             | Files                                                 |
| --------------------------------------------------- | ---------- | ----------------- | --------------------------------------- | ----------------------------------------------------- |
| [#689](https://github.com/kosedge/kosedge/pull/689) | `f33637db` | PR Quality Checks | Check formatting (`prettier --check .`) | inventory json/md, t5098u checkpoint, t5105u addendum |
| [#690](https://github.com/kosedge/kosedge/pull/690) | `cc594b6f` | PR Quality Checks | Check formatting (`prettier --check .`) | same four files                                       |

Unrelated baseline CI: none failed besides Prettier. Passed on both drafts: Vercel Preview Comments, Vercel – kosedge, Vercel – kosedge-vercel-push, inspiring-curiosity - kosedge. Lint / typecheck / tests were skipped after the format fail — not an independent failure.

Prettier `--write` applied to those four files only. No workflow / ignore-file waiver. PRs stay DRAFT.

## Exact blockers (missing field / artifact)

IF-dependent scoring leg (control + challenger) for 2020–23 REG is **blocked**, not silently dropped:

| Artifact                     | Detail                                                            |
| ---------------------------- | ----------------------------------------------------------------- |
| `RECON_MATRIX_2020_2023_REG` | only 2017 W7–W17 recon matrix exists                              |
| `b41f4b43_hist_inputs`       | IF hist inputs reconstruction MISSING (paper §2)                  |
| `if_tree_6ca03716`           | frozen IF checkout not mounted on this sparse worker              |
| `archived_IF_mus_2020_2023`  | no in-repo IF mus @ 6ca03716 for 2020–23 (2017 only)              |
| `outcomes_2023_score_only`   | `50bda875` extract stops at 2022; 2023 in-season Q2 as-of blocked |

Q2 2020–22 as-of can run when `games_4fe1cdd7` + `outcomes_2013_2022_score_only` are supplied (not copied into this sparse worktree). Independent reconstruction tests and synthetic boundaries continued.

## Out of scope (not done)

Real EXEC scoring · Alex preflight · CoS one-run bind · merge/deploy · paid Odds · Stage C · new features/algorithms · post-EVAL retune · silent IF drop · invented ATS/OU probs.

Next: Alex preflight GO, then CoS bind of this FROZEN_MANIFEST + one conditional EXEC.

STOP · CERT=0 · DRAFT only
