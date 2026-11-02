# Experiment E — kickoff-honest as-of audit (t4586u / t4598u)

**EXP E ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · sealed=1 · #648 DRAFT · do not merge**

**VERDICT: `PASS`** · `n_kickoff_fail=0`

## Authority

| item | sha8 |
|---|---|
| Ryan CLEAR t4598u | 5bb608d0 |
| CoS execute order | 701ac13c |
| IMV PASS_PROTOCOL v2 | 60c18a4c |
| Cursor FEASIBILITY v1.1 | 15ee3a1b |
| Alex SPEC | ddffb72e |
| ESTIMATOR addendum | 84a28a05 |
| Cursor ACK | 6fcc0af6 |
| games.csv pin | 4fe1cdd7 |
| #646 rolling CSV | 1b07654e |

## counts.json (v1.1 §1.7)

| key | value |
|---|---:|
| `n_games` | 2992 |
| `n_windows` | 5984 |
| `n_windows_empty` | 0 |
| `n_rows_season_ge_2024` | 0 |
| `n_invariant6_game_id_diff` | 0 |
| `n_franchise_alias_drop` | 0 |
| `n_contributors` | 29920 |
| `n_kickoff_ok` | 5984 |
| `n_kickoff_fail` | 0 |
| `n_kickoff_unknown` | 0 |
| `n_self_game_leak` | 0 |
| `n_week1` | 175 |
| `n_covid_flex_flags` | 0 |
| `n_intraweek_conservative` | 14541 |
| `n_franchise_cross` | 0 |
| `n_rest_placeholder` | 2992 |
| `n_neutral` | 55 |

`n_windows_empty_exception_list` = `[]`

`games_csv_sha256` = `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8`

## Artifact sha8

| artifact | sha8 |
|---|---|
| `counts.json` | `b0365365` |
| `covid_flex_flags.csv` | `531cadcc` |
| `games.csv` | `4fe1cdd7` |
| `historical_oos_games.csv` | `1ee90fac` |
| `intraweek_conservative.csv` | `a67c89e2` |
| `inversions.csv` | `62ac348e` |
| `kickoff_unknown.csv` | `d8cece63` |
| `manifest.json` | `aa9d37e0` |
| `neutral_catalog.csv` | `14a48a60` |
| `pbp_weather_game_2012_2023.csv` | `6934509a` |
| `play_by_play_2012.parquet` | `447b9078` |
| `play_by_play_2013.parquet` | `f454605a` |
| `play_by_play_2014.parquet` | `54c01408` |
| `play_by_play_2015.parquet` | `01b5ae7d` |
| `play_by_play_2016.parquet` | `95eba04e` |
| `play_by_play_2017.parquet` | `84eacd96` |
| `play_by_play_2018.parquet` | `2e6f2dce` |
| `play_by_play_2019.parquet` | `60c30670` |
| `play_by_play_2020.parquet` | `8889f5d8` |
| `play_by_play_2021.parquet` | `333ad343` |
| `play_by_play_2022.parquet` | `931121d8` |
| `play_by_play_2023.parquet` | `bd348473` |
| `rest_catalog.csv` | `82b956ec` |
| `rolling_features_weekly_pbp_strict_asof_2013_2023.csv` | `1b07654e` |
| `schedule_2012_offpanel_kickoffs.csv` | `d36bbb12` |
| `week1_windows.csv` | `08ef1fa3` |

## Blocked / fail reasons

- blocked: none
- fail: none

## Notes

- vintage_mismatch=0
- 2012_snapshot_rows=267
- offpanel_rows=267
- weather_rows=3259

## Explicit non-runs

- Exp A not run. β not fit. `simulate_nfl_game` not imported.
- LOCKED_SCORING / config_overrides untouched.
- Odds API not called. DATABASE_URL not required.
- #646/#647/#648 not merged. 2024+ not used. F2 PHI@WSH not touched.
- CERT=0. No fireable claim.

NFL NO-GO · Coming Soon ON · F2 frozen · sealed=1
