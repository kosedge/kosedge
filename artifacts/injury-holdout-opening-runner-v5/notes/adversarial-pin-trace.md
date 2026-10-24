# Adversarial pin-trace (v5) — every production input to a pin

No production input is taken from an unpinned games.json value.

| Input | Source | Pin |
| --- | --- | --- |
| Scorer | `seeded/v6.2-draft/run_injury_residual_evaluator.py` | `755d30a8` (exactly one; no runtime switch) |
| Scorer diff baseline | `seeded/ca98ae0e/run_injury_residual_evaluator.py` | `ca98ae0e` |
| Ryan scorer decision | `/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt` | `592e0bb9` |
| CLEAR | `seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt` | `fabf8732` |
| Frozen script | `seeded/run_injury_residual_fit.py` | `8d188da2` |
| Fit object | `seeded/fit_object.json` | `6a5490db` |
| Null contract | `seeded/nfl_injury_null_contract_8e2a15ac.py` | `ff8e6527` |
| Writer | `seeded/write_sealed_injury_export_ts_v1.py` | `9947b880` |
| QB1_INDEX_UNITS | `seeded/injury_paths_8e2a15ac.py` `QB1_INDEX_UNITS = 0.12` | `ebd3dac0` / HEAD `8e2a15ac` |
| Row builder | `holdout_frozen_row_builder.py` | `aa9d512b` |
| Delta producer | `holdout_delta_producer.py` | `6409dcb8` |
| Baseline method | `record_hfa_baseline_method.py` | `76aac887` |
| le2023 export | `seeded/sealed_injury_export_ts_v1.json` | `a38a55bb` (on-disk `.sha256.v2`) |
| Frozen export | `seeded/sealed_injury_export_d87e6129.json` | `d87e6129` (untouched) |
| Schedule raw | `seeded/raw-le2023/schedule/games_reg_le2023.csv` | `ce80fe92` |
| Rosters raw | `seeded/raw-le2023/rosters/roster_YYYY.csv` | per-year shas in expected |
| Listings raw | `seeded/listings-le2023/listings_YYYY.csv` | per-year shas in expected |
| Record baseline CSV | `inputs/record_baseline_le2023.csv` | `502110cf` |
| nflverse close | `inputs/nflverse_close_le2023.csv` | `634d8e73` |
| Request fold years | `seeded/nfl-injury-holdout-request-2024-2025-v3.1.md` `season ∈ {2024, 2025}` | `35cbb56e` |
| Spec / acceptance | seeded copies | `a156459b` / `54bc78ec` |
| Expected answers | `t_expected/HOLDOUT_EXPECTED.json` | hashed after this file is written |
| games.json | identity-only (season, week, home, away) | values / x_continuity / deltas **refused** |
| Listings timestamps | `date_modified` | Z or offset; naive **STOP** |

Production workspace paths (B-13, existence/headers only before lock):
`/workspace/ops/nfl_injury_audit_t4274u/{listings/,schedule.csv,rosters/,close.csv,games.json}`.
Schedule requires `gameday` + `gametime`. After lock, the builder
reads those raw files; it does not read player value from games.json.

If the v6.2 sha changes again, IMV must re-check the diff versus
`ca98ae0e` as holdout-allowance-only, no metric change.
