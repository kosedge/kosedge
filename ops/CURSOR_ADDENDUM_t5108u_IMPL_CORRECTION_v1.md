# CURSOR ADDENDUM t5108u — implementation correction v1

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER t5108u IMPLEMENTATION CORRECTION (not a new experiment / not a scoring waiver)
Continue under t5107u G1–G7 on the same #691 branch.

## Preserve

| Pin | Value |
| --- | --- |
| PR | https://github.com/kosedge/kosedge/pull/691 (DRAFT) |
| Parent tip (Ryan inspected) | `a0cc26564eac995dac0bacc0443ecd1850ed21d4` |
| This tip | `TIP_PENDING` |
| Design seal (body, not a forecast freeze) | `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd` |
| Appended manifest sha256 | `ecbdf98a3610eb21256c9ad195ab050ed56fd227a8f8095d76fc685192bd3e96` |
| Paper tip | `7139f8d9eed71b47eabf8827c0593932a38fea9a36686c66df3f6311282628c7` |
| IF tip / simulator / framework | `6ca03716` / `52d9e909` / `a0051cc4` |
| 2023 PBP publisher | `4aeca98ebe6357c5f1a13165533007964605d1f17bd54561937769b952c67613` |

PRs remain DRAFT. No merge / deploy / paid Odds. No real EVAL. No Stage C. No invented efficiency/index formulas.

## What Ryan found at a0cc26564 (fixed)

1. `run_eval_score` returned placeholder `NOT_AUTHORIZED_IN_THIS_PACKAGE`.
2. IF path consumed a supplied reconstructed μ instead of producing it.
3. Design-only `FROZEN_MANIFEST` must not be presented as a forecast freeze.

## CoS execution

1. **IF tree fetched** via ordinary git worktree: `/tmp/t5108u-if-6ca03716` @ `6ca03716fe52930332d5ffba302c312a651980cc`. “Sparse not mounted” is not used as a missing-source claim. File hashes match `52d9e909` / `a0051cc4`.
2. **produce-μ** (`if_produce.py` → `resolve_if_margin`): frozen IF + complete DERIVED_PREGAME packet produces `if_margin_mu`. Supplied `reconstructed_margin_mu` / `reconstructed_if_mus` refused. Rest bound from packet. `market_blend=0`, 4000 sims, seed `201710+sha256(game_id)%1000003`.
3. **Executable paired-margin evaluator** (`run_paired_margin_eval`): synthetic E2E with hand-checkable values (see tests). `run_eval_score` remains gated on persistent one-run + Alex GO + CoS bind.
4. **Bootstrap**: signed per-game loss diffs `L_c−L_ctrl`; CI on **MEAN**; game + season-week cluster; `B=10000` seed `20261101`. Negative paired improvement unit-tested (mean −2.5 vs IF; CI excludes 0).
5. **Cohorts**: `freeze_eligible_cohorts` freezes per-metric sets after cutoff/quote eligibility, before outcome join.
6. **One-run**: `one_run.py` atomic persist of effective-spec / code / input / forecast / cohort hashes + Alex GO id. Duplicate and mismatch refused.
7. **Manifest**: original design body hash still `e5bb682d`. Appended `input_bindings` + `design_seal_is_forecast_freeze=false`. Appended file hash `ecbdf98a`.
8. **Inputs**: opened only 2020–23 under `/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01/`. Extracted 2023 REG schedule/results (n=272) and 2020–23 (n=1071). Hashed. No Stage C. No invented efficiency/index formulas. No paid pulls.

## Tests

```
cd services/model-service && PYTHONPATH=. python3.11 -m pytest \
  tests/test_nfl_odds_reader.py \
  tests/test_nfl_odds_comparison_harness.py \
  tests/test_nfl_forecast_builder_t5107u.py \
  tests/test_nfl_real_data_evaluator_t5107u.py \
  tests/test_nfl_t5108u_impl_correction.py -q
.........................................................  57 passed
```

- Prior reader+harness: **26/26**
- Builder (updated guards): **13**
- Evaluator (updated gate): **8**
- t5108u correction: **10**
- Combined: **57/57**

Covered: produce-μ from frozen tree; refuse supplied reconstructed μ; signed MEAN bootstrap; negative paired improvement; freeze-after-eligibility; one-run duplicate/mismatch; real-eval gate; synthetic numerical runner; design-seal preserve; 2023 extract; sealed-season refuse.

## Prepared input hashes

| File | n | sha256 |
| --- | ---: | --- |
| `inputs/schedule_results_2020_2023.csv` | 1071 | `0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479` |
| `inputs/schedule_results_2023.csv` | 272 | `253e178b72094f809264ff7a38b6792fbd99ffac092b26a00a8e8693416a63da` |
| `inputs/INPUT_BINDINGS.json` | — | `68b94b6bebd5ed33d40559e98137a1ff9b686bc93adf99ffde8b540b587856e1` |

2024–26 PBP files were not opened.

## Input availability

| Input | Status | Owner | Dependent field |
| --- | --- | --- | --- |
| nflverse PBP archive 2020–23 | available | owned archive `/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01/` | schedule / scores extract |
| prepared schedule_results_2020_2023.csv | hashed | t5108u inputs.py | game identity / scores / game_date / rest_days |
| prepared schedule_results_2023.csv | hashed | t5108u / publisher `4aeca98e` | 2023 REG outcomes + Q2 as-of scores |
| frozen IF tree 6ca03716 | available | git tip `6ca03716fe52930332d5ffba302c312a651980cc` | produce-μ reconstruction |
| games.csv 4fe1cdd7 kickoff TZ | MISSING | Q2 extract / t5009u games.csv | `kickoff_utc` (KO−60; same-day as-of order) |
| outcomes extract 50bda875 | MISSING | Q2 outcomes extract (stops 2022) | pre-2023 scored history file (2023 scores now from PBP) |
| PBP start_time timezone | MISSING | t5105u TZ contract / nflverse `start_time` is naive | `kickoff_utc` |
| b41f4b43 hist inputs / efficiency+index 5g | MISSING | t4873u / paper §2 — do not invent formulas | `offense_index_*`, `defense_index_*`, `*_epa_5g`, `*_pass_rate_5g`, `*_success_*`, `matchup_diff_*` |
| RECON_MATRIX_2020_2023_REG | MISSING | IF recon matrix owner (2017 only @ b56be146) | same efficiency/index fields |
| archived IF mus 2020–23 @ 6ca03716 | MISSING | IF archive / 19c6a4607 consume lineage | `if_margin_mu` (archived) |
| Stage C / scored columns | FORBIDDEN | held — not a missing-to-invent source | none (refused) |

## Blockers (still blocking real EVAL / full IF reconstruction)

| Artifact | Owner | Dependent field | Notes |
| --- | --- | --- | --- |
| b41f4b43 hist inputs | t4873u / paper §2 | efficiency + index 5g packet fields | no invented formulas |
| RECON_MATRIX_2020_2023_REG | IF recon matrix owner | same | only 2017 W7–W17 exists |
| archived IF mus 2020–23 | IF archive | archived `if_margin_mu` | produce-μ can substitute when packet is complete |
| kickoff_utc timezone | t5105u / Q2 games.csv 4fe1cdd7 | KO−60 cutoff, same-day as-of | PBP `start_time` is naive |
| Alex GO + CoS one-run bind | Alex / CoS | `run_eval_score` | synthetic runner is live; real EVAL refused |
| Forecast freeze | builder after complete packets | EXEC scoring | design seal ≠ forecast freeze |

## Not done / not claimed

- No real 2022–23 EVAL pass.
- No forecast-hash freeze of a full 2020–23 slate (efficiency packet incomplete).
- No Stage C. No paid pulls. No criteria relaxation. No second experiment.
- Design seal `e5bb682d` remains design/input-source/fit-policy only.

HARD END 15:00 ET. DRAFT only.
