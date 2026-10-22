# W8 fetcher STOP scope — caller list

The six engine DB fetchers STOP only when `W8_CAPTURE_BUILD` is set
(inside `w8_build_context` / `predict_stream` / `build_and_seal`).
They do **not** STOP merely because `session is None`.

Reason: `fetch_current_qb1(None, …)` is a real packaged-SoT path when
the depth file covers ≥24 teams. A session-None STOP outside W8 would
break that path.

## Fetchers

| function | module |
| --- | --- |
| `fetch_prior_primary_qbs` | `nfl_season_engine.continuity_score` |
| `fetch_current_qb1` | `nfl_season_engine.continuity_score` |
| `fetch_roster_sets` | `nfl_season_engine.continuity_score` |
| `fetch_skill_yards_by_player` | `nfl_season_engine.continuity_score` |
| `fetch_team_proe_map` | `nfl_tendency_pricing` |
| `fetch_team_direction_rates` | `nfl_tendency_pricing` |

## Every caller

| caller | fetcher | session | relies on session-less? |
| --- | --- | --- | --- |
| `continuity_score.build_continuity_book` | prior QB / current QB1 / roster ×2 / skill-yards | live `session` | no |
| `tasks.py` (~l.1238) `build_continuity_book(...)` | same six via the book (prior QB / current QB1 / roster ×2 / skill-yards) | live `session` | no |
| `qb_premium` (QB book build) | `fetch_current_qb1`, `fetch_prior_primary_qbs` | live `session` | no |
| `tasks.py` (~4775, ~15220) | `fetch_team_proe_map` | live `session` | no |
| `tests/test_nfl_depth_sot_audit.py:150` | `fetch_current_qb1(None, season=2026, as_of_week=1)` | **None** | **yes — packaged SoT exclusive when ≥24 teams** |
| `tests/test_nfl_w8_fail_closed.py` `test_f3_db_loader_fallback_fails_closed` | `fetch_current_qb1(session, season=1999)` | mock session | no |
| `tests/test_nfl_w8_fail_closed.py` `test_f6_reaching_db_loader_during_w8_build_is_stop` | four continuity fetchers | mock session **inside** `w8_build_context` | no (W8 STOP) |

`fetch_team_direction_rates` has **no production or test caller** besides
its definition. No caller relies on a session-less path for the other
five fetchers except `fetch_current_qb1(None)` in the depth SoT audit.

## Decision

Scope the STOP to W8 builds (`W8_CAPTURE_BUILD`). Do not refuse
session-less calls outside W8.
