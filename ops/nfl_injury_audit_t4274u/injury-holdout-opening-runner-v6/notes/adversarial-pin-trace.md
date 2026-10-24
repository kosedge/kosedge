# Adversarial pin-trace (v6) — every claim to a deposited file

No production input is taken from an unpinned games.json value.
Every claim below names the deposited file IMV can hash.

| Input / claim | Deposited file | Pin |
| --- | --- | --- |
| Active scorer (L-1 FINAL) | `seeded/v6.2/run_injury_residual_evaluator.py` | `8b482cb9` (exactly one; no runtime switch) |
| L-1 docstring-only | `seeded/v6.2/DIFF_vs_755d30a8.txt` | `280d9785` (3 header lines) |
| v6.2 content PASS baseline | `seeded/v6.2-755d30a8/run_injury_residual_evaluator.py` | `755d30a8` |
| Scorer diff vs v6.1 | `seeded/ca98ae0e/run_injury_residual_evaluator.py` | `ca98ae0e` |
| Ryan scorer decision | `/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt` | `592e0bb9` |
| RETURN v5 | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v5.txt` | `2c71e4d0` |
| CLEAR | `seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt` | `fabf8732` |
| Frozen script | `seeded/run_injury_residual_fit.py` | `8d188da2` |
| Fit object | `seeded/fit_object.json` | `6a5490db` |
| Null contract | `seeded/nfl_injury_null_contract_8e2a15ac.py` | `ff8e6527` |
| Writer | `seeded/write_sealed_injury_export_ts_v1.py` | `9947b880` |
| QB1_INDEX_UNITS | `seeded/injury_paths_8e2a15ac.py` `QB1_INDEX_UNITS = 0.12` | `ebd3dac0` / HEAD `8e2a15ac` |
| Row builder | `holdout_frozen_row_builder.py` | `247744d2` |
| Delta producer | `holdout_delta_producer.py` | `ae8f9585` |
| Baseline method | `record_hfa_baseline_method.py` | `76aac887` |
| le2023 export | `seeded/sealed_injury_export_ts_v1.json` | `a38a55bb` (on-disk `.sha256.v2`) |
| Frozen export | `seeded/sealed_injury_export_d87e6129.json` | `d87e6129` (untouched) |
| B-4b(R) rebuilt deltas | `out/le2023/rebuilt_le2023_deltas.json` | `8af44a7e` (n=2863) |
| B-4b(R) compare | `out/le2023/rebuilt_le2023_compare.json` | `bc89721f` (`0_DIFF` vs `a38a55bb`) |
| Schedule raw (le2023) | `seeded/raw-le2023/schedule/games_reg_le2023.csv` | `ce80fe92` |
| Rosters raw (le2023) | `seeded/raw-le2023/rosters/roster_YYYY.csv` | per-year shas in expected |
| Listings raw (le2023) | `seeded/listings-le2023/listings_YYYY.csv` | per-year shas in expected |
| Record baseline CSV | `inputs/record_baseline_le2023.csv` | `502110cf` |
| nflverse close | `inputs/nflverse_close_le2023.csv` | `634d8e73` |
| Request fold years | `seeded/nfl-injury-holdout-request-2024-2025-v3.1.md` `season ∈ {2024, 2025}` | `35cbb56e` |
| Spec / acceptance | seeded copies | `a156459b` / `54bc78ec` |
| Expected answers v6 | `t_expected/HOLDOUT_EXPECTED.json` | `0c31243d` |
| games.json | identity-only (season, week, home, away) | values / x_continuity / deltas **refused** |
| Listings timestamps | `date_modified` | Z or offset; naive **STOP** |

B-4b(P) production raw inputs (hashed into lock + receipt **before
any row parse**):
`/workspace/ops/nfl_injury_audit_t4274u/{listings_*.csv,schedule.csv,roster_*.csv,close.csv,games.json}`.
This package has none of those production files. The runner still
implements the hash-into-lock-and-receipt contract. Fixture E2E
records the fixture-workspace raw shas the same way.

B-4b(n) allowed roster years: le2023 2012–2023; production
{2023,2024,2025}; synthetic {2098,2099}; 2026 never.

If the v6.2 sha changes again past `8b482cb9`, IMV must re-check
the new diff.
