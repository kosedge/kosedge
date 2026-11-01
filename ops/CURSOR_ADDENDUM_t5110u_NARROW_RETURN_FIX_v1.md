# CURSOR ADDENDUM t5110u — narrow RETURN fix v1

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: Alex RE-PREFLIGHT RETURN **69710b9c** · CoS ORDER t5110u · same #691

## Preserve

| Pin                                       | Value                                                              |
| ----------------------------------------- | ------------------------------------------------------------------ |
| PR                                        | https://github.com/kosedge/kosedge/pull/691 (DRAFT)                |
| Parent tip (Alex inspected)               | `7168c3794dc5b2d69b58e32a271adea9ff6fb624`                         |
| Implementation parent                     | `2058e78b3cb328fd318a3e7c9f239cffc96b4658`                         |
| This tip                                  | `c71057f7c1c3aeb882a064b81aaaafb98610ddde`                         |
| Design seal (not a forecast freeze)       | `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd` |
| Appended manifest sha256 (canonical body) | `f3e5e4b96bf1f2983ceba13ec455f4f39f040e5bb43bedcdf0a81b927bb34711` |
| Alex RETURN                               | `69710b9c40b3a19b0d259bb65a208d9ecc15296b49eae9843aa356d250c9c62a` |
| t5108u addendum                           | `0b0afcc2d2c266ee89fe3a4da5e90ee608d7917460c9ee22b8465f4dce30ba2e` |

No merge / deploy / paid Odds. No real EVAL. No Stage C. No invented b41f4b43 formulas.

## Narrow fixes (only the RETURN items)

1. **bootstrap_ci default** is `mean_stat` (MEAN of signed per-game loss diffs), not `paired_mae`. `test_bootstrap_ci_default_is_mean_of_signed_diffs` calls `bootstrap_ci(diffs)` with no `stat=` on negative diffs → CI upper < 0.
2. **One-run:** `run_eval_score` marks the record **CONSUMED** after a successful score; second execution refused. Exclusive create (`O_CREAT\|O_EXCL`). `verify_one_run` re-hashes code/spec/input at run time (path or live sha) and refuses mismatch / missing rehash.
3. **Prettier:** `prettier@3.3.3 --write` + `--check` green on the 3 files that failed PR Quality Checks @7168c379:
   - `data/ops/nfl-forecast-builder-t5107u/FROZEN_MANIFEST.json`
   - `data/ops/nfl-forecast-builder-t5107u/inputs/INPUT_BINDINGS.json`
   - `ops/CURSOR_ADDENDUM_t5108u_IMPL_CORRECTION_v1.md`
4. **Pins:** full sha games.csv **`4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8`**. kickoff_utc is **NOT missing** (UTC Z for 2020–23; Alex 69710b9c + pin sidecar 8155fd194). Outcomes **`50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081`**. Quote/odds join manifest **`6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984`** (`data/ops/nfl-odds-reader-2020-2023-join-manifest.json`).
5. **IF packet:** b41f4b43 hist inputs + RECON*MATRIX_2020_2023_REG remain **MISSING** (owner t4873u / paper §2 / recon-matrix owner → `offense_index*_`, `defense*index*_`, `_\_epa_5g`, `**pass_rate_5g`, `\*\_success**`, `matchup*diff*_`). Produce-μ stays ready. No invented formulas. No Stage C.

## CI disclosure

@7168c379 (Alex 69710b9c):

| Check                        | Status   | Notes                                            |
| ---------------------------- | -------- | ------------------------------------------------ |
| PR Quality Checks / Prettier | **FAIL** | 3 files above — not disclosed in t5108u addendum |
| Vercel                       | pass     | —                                                |
| Railway                      | pass     | —                                                |

This tip formats those 3 files with `prettier@3.3.3 --check` green locally. GitHub PR Quality Checks on the new head are not yet observed in this addendum (disclose after CI runs).

## Tests

```
cd services/model-service && PYTHONPATH=. python3.11 -m pytest \
  tests/test_nfl_odds_reader.py \
  tests/test_nfl_odds_comparison_harness.py \
  tests/test_nfl_forecast_builder_t5107u.py \
  tests/test_nfl_real_data_evaluator_t5107u.py \
  tests/test_nfl_t5108u_impl_correction.py -q
# 59 passed
```

Prior 57 retained + 2 t5110u (`bootstrap_ci` default signed MEAN; runtime rehash refuse). Consumed-second-execution covered in the existing one-run numerical test.

## Input availability (appended; design seal unchanged)

| Input                                      | Status    | sha256                  | Owner / dependent                                                       |
| ------------------------------------------ | --------- | ----------------------- | ----------------------------------------------------------------------- |
| games.csv 4fe1cdd7 kickoff_utc             | hashed    | `4fe1cdd7f2eb…abef8`    | Q2/t4422u → kickoff_utc **NOT missing** (UTC Z 2020–23)                 |
| outcomes 50bda875                          | hashed    | `50bda875daa8…dc081`    | Q2 2013–2022 score-only; 2023 scores from PBP `253e178b`                |
| quote/odds join manifest                   | hashed    | `6a1c1b378b91…e6984`    | t5105u reader join manifest                                             |
| b41f4b43 hist inputs / efficiency+index 5g | MISSING   | `b41f4b43`              | t4873u / paper §2 → IF packet fields (blocks produce-μ on real 2020–23) |
| RECON_MATRIX_2020_2023_REG                 | MISSING   | 2017 only @ b56be146    | IF recon matrix owner → same fields                                     |
| archived IF mus 2020–23                    | MISSING   | `6ca03716`              | IF archive → archived μ; substitutable by produce-μ when packets exist  |
| Stage C / scored columns                   | FORBIDDEN | `1ee90fac`              | held — not a missing-to-invent source                                   |
| frozen IF tree 6ca03716                    | available | `52d9e909` / `a0051cc4` | produce-μ reconstruction                                                |

## Still blocking real EVAL / GO

- Complete DERIVED_PREGAME packets (b41f4b43 + RECON_MATRIX) for 2020–23 REG — zero scorable G1 legs until then
- Alex GO + CoS one-run bind (procedural; not issued)
- Design seal ≠ forecast freeze
- GitHub Prettier on this new head not yet observed

HARD END 15:00 ET. DRAFT only.
