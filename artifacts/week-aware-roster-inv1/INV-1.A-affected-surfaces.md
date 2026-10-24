# INV-1.A — affected surfaces

Line numbers from pinned v6-branch copies (scripts are not on
`deploy-vercel` HEAD `20d51f22`). Holdout years 2024–25 were not opened
on any surface below.

Leak fields: **membership** / **depth** / **role** / **status**.
Season-level `roster_YYYY.csv` is one row per `(team, gsis_id)` with a
`week` stamp that is usually last-week or playoff. Loaders ignore `week`.

## A1. Injury builder / nowcast path

| id | path | sha8 | symbol | lines | leak | seasons touched | 2024–25 opened |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1-LOAD | `holdout_frozen_row_builder.py` | `247744d2` | `load_rosters_dir` | 267–302 | membership, depth, role | declared roster years (le2023 = 2012–2023) | NO |
| A1-BUILD | same | `247744d2` | `build_rows` | 327–329 | wires leaked maps into `precompute_games` | same | NO |
| A1-FITLOAD | `run_injury_residual_fit.py` | `8d188da2` | `load_rosters` | 289–314 | membership, depth, role; `week`/`game_type`/`status` unread | 2012–2023 files; books from 2013 | NO |
| A1-PRE | same | `8d188da2` | `precompute_games` | 458–497 | identity + depth + value + current_ids | FIT_YEARS 2013–2023 | NO |
| A1-UNITS | same | `8d188da2` | `side_units` | 534–562 | applies leaked `value` / QB1 | 2013–2023 | NO |
| A1-WRITE | `write_sealed_injury_export_ts_v1.py` | `9947b880` | export path | 338–345 | `fit.load_rosters()` + `precompute_games` | 2013–2023 | NO |

Production `injury_paths.py` has no `load_rosters` / `STARTER_SLOTS` /
`_structural_index`. Overlays remain disabled. Not a residual-fit feeder.

## A2. Replacement-quality / identity (C-11)

| id | path | sha8 | symbol | lines | leak | 2024–25 opened |
| --- | --- | --- | --- | --- | --- | --- |
| A2-VAL | `run_injury_residual_fit.py` | `8d188da2` | `precompute_games` | 466–485 | depth, role (`value`, `is_qb1_out_candidate`); `STARTER_SLOTS` treats every `QB` slot as depth 1 | NO |
| A2-IDX | same | `8d188da2` | `_structural_index` | 149–176 | maps leaked depth 1/2 to replacement weight | NO |
| A2-IDENT | `nfl_injury_null_contract_8e2a15ac.py` | `ff8e6527` | `resolve_fit_player_identity` | 658–688 | helper; leak is season-union books passed in (TEAM_MATCH / SEASON_FALLBACK) | NO |
| A2-IDENTCALL | `run_injury_residual_fit.py` | `8d188da2` | `precompute_games` | 458–464 | identity against `roster_by_team[season]` / `roster_season[season]` | NO |

Status of the *listing* is week-as-of (IMV judged safe). Status of the
*roster snapshot* (`ACT`/`RES`/`CUT`/`INA`/`DEV`) is unread by the
loader but the row still enters membership.

## A3. Historical fit (le2023 and earlier)

| id | path | sha8 | symbol | lines | leak | 2024–25 opened |
| --- | --- | --- | --- | --- | --- | --- |
| A3-MAIN | `run_injury_residual_fit.py` | `8d188da2` | `main` | 774–778 | entire fit run | NO |
| A3-APPLY | same | `8d188da2` | `apply_params` / `residual_from_units` | 565–718 | deltas from leaked units + `x_continuity` | NO |
| A3-OBJ | `fit_object.json` | `6a5490db` | selected Spec C | n/a | product of A3-APPLY | NO |
| A3-EXP | path-1 export | `a38a55bb` | sealed export | n/a | product of A1-WRITE | NO |

These hashes may be cited as **SUPERSEDED** evidence only. They are not
certified week-aware results.

## A4. Continuity (within-season future)

| id | path | sha8 | symbol | lines | leak | R-6 note | 2024–25 opened |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A4-CONT | `run_injury_residual_fit.py` | `8d188da2` | `continuity_for_team` | 355–396 | `current_ids` = current-season union (hides week-1 departures when a later signing exists) | prior-year book is season-union of S-1 (temporally complete before S week 1) but current side **does** leak within-season future | NO |
| A4-CUR | same | `8d188da2` | `precompute_games` | 489–497 | passes season-union `current_ids` | same | NO |

R-6 is **not** satisfied by the current implementation. A prior-year-only
continuity feature could be restated later if the current side is
week-aware. That restatement is not claimed here.

Production `nfl_roster_continuity.py` is a human-curated offseason
multiplier, not residual-fit `x_continuity`.

## A5. Producer / baseline "pre-kickoff only" claim

| id | path | sha8 | symbol | lines | leak | 2024–25 opened |
| --- | --- | --- | --- | --- | --- | --- |
| A5-CLAIM | `holdout_delta_producer.py` | `ae8f9585` | module docstring + `_pre_kickoff_only` + `_assert_as_of_before_kickoff` | 12, 78–99, 128–129 | claim covers `listing_as_of` and post-game scores only; roster `week`/`availability_ts` never checked | NO |

## A6. Evaluator / runner / expected-answers text

Opening-runner v6 package (unmerged; paused) freezes the defective
"pre-kickoff only" claim and the season-level builder as the SoT for
`value` / `x_continuity`. That package is **not** reopened here.

Leftover untracked `run_injury_residual_holdout_v3.py`
`load_holdout_rosters` L812–840 uses the same collapse and would read
2024/2025 if executed. **Not executed. Not staged.**

## Adjacent (not residual-fit feeders)

- `services/model-service/src/services/nfl_season_engine/injury_paths.py` — no season-level roster load
- `services/data-platform-nfl/src/data_platform_nfl/ingest.py` `materialize_depth_chart_weekly` L1735–1795 — `SELECT FROM nfl_dp_rosters WHERE season=:season` (no week). Adjacent class.
- Packaged W1 depth (`load_packaged_depth_chart`) — season-engine nowcast, not residual-fit input
