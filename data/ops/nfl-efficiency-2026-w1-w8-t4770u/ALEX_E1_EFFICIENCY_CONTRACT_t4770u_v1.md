# ALEX — H-IFT-1 E1 EFFICIENCY INPUT CONTRACT · t4770u · v1
Filed 2026-10-30 ET · PAPER/CONTRACT ONLY · ≠emit ≠E2 ≠Odds ≠C10 ≠retune ≠redesign ≠new hypothesis

## 1. Authority + locks
| Item | sha8 / pin | Status |
|---|---|---|
| DECISION_RYAN_t4770u_HIFT1_EFFICIENCY_RECOVERY.md | 751dd63c (751dd63c34c5ac81…2913a) | recomputed MATCH |
| COS_ORDER_ALEX_t4770u_EFFICIENCY_CONTRACT.txt | 289e19d7 (289e19d77a678270…1513fe6) | recomputed MATCH |
| E1 FAIL_CLOSED ALEX_E1_IF_TOTALS_EMIT_t4768u_v1.md | ebfcd85b | recomputed MATCH |
| Paper ALEX_FALSIFIABLE_HYPOTHESIS_t4757u_v2.md | ec343df3 | recomputed MATCH, untouched |
| IMV PASS_PAPER IMV_GRADE_t4761u_HIFT1_V2.txt | 3e4a8c66 | recomputed MATCH, untouched |
| IF code git | 1b39f4e9 (1b39f4e9f6b2e04c264a41831f3bb7273e475011) | /tmp/e1_1b39 HEAD |
| nfl_simulator.py @1b39f4e9 | 52d9e909 (52d9e90927c9bc9d…6385) | MATCH |
| nfl_matchup_features.py @1b39f4e9 | 107151d6 | read |
| data_platform_nfl/ingest.py @1b39f4e9 | 33f2bf4e | read (rolling builder) |
| infra/db/016_nfl_matchup_features.sql | 8d10d795 | read (schema) |
| sim pin baseline | 9b61c5c3 | flag-OFF byte-identical (d3_evidence cd014a2b) |
| a4b88ae8 | CLEAR-A post-merge RECEIPT sha8 — not a git ref | note |

Locks: NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · Odds HOLD 70c56700 · overlays OFF · weather/injury OFF · no DK in E1 · no −110 invent.

## 2. Preflight t4293u (registers RO, no edits)
| Asset | Class | Cite |
|---|---|---|
| nfl_simulator.py (pin 9b61c5c3 / IF 1b39f4e9) | EV | MODEL_MODULES.md row "NFL simulator"; d3_evidence D3(i)/(ii) PASS |
| Packaged 2026 schedule (15 W9 games) | EV (packaged, verified) | w09_input_manifest schedule sha d88ae734 |
| 2026 W1–W8 PBP / team situational / rolling 5g | **M** | ebfcd85b; manifest efficiency_current=MISSING |
| nfl_team_efficiency_backbone_2026.json / epa_priors_2026.json | EV-as-2025-prior · **forbidden for E1** | manifest priors 4cd45f85 / a4e3fa90 |
| NFL Postgres dumps (Jul 2026) | EU, pre-season → no W1–W8 | DATA_ASSETS.md row "NFL Postgres dumps" |
| Box NFL feature inventory t4183u | EV (not in-season 2026 eff.) | DATA_ASSETS.md cf9ebb2f |
| nflverse 2026 PBP (approved no-cost) | SU — pending Cursor DATA_* | DECISION 751dd63c §Cursor 1–6 |
| nflverse market lines | EV diagnostic only, never gate; not E1 input | DATA_ASSETS.md MS-9 03ea570b |
| Handicap framework (decomposition consumer) | EU | MODEL_MODULES.md |

## 3. Minimum field set (NflGameInputs @1b39f4e9) — 20 REQUIRED efficiency fields
Consumption: `simulate_nfl_game_independent_fair` → `simulate_nfl_game(independent_fair=True)` → `_build_matchup_adjustments`, `_build_totals_adjustments`, `compute_nfl_projection_decomposition`.
Note: matchup `home_points=0.72·spread+0.57·total`, `away_points=−0.58·spread+0.43·total` → spread_signal leaks 0.14× into total_mu, so the spread-signal diff fields ARE total-relevant.

| # | Field | Code default if missing | E1 rule |
|---|---|---|---|
| 1–2 | offense_index_home / _away | 1.0 (dataclass) | REQUIRED, explicitly sourced |
| 3–4 | defense_index_home / _away | 1.0 | REQUIRED |
| 5–6 | home_off_epa_5g / away_off_epa_5g | None→0.0 | REQUIRED |
| 7–8 | home_def_epa_allowed_5g / away_ | None→0.0 | REQUIRED |
| 9–10 | home_pass_rate_5g / away_ | None→0.57 (totals) / 0.0 (matchup) | REQUIRED |
| 11–12 | home_success_offense_5g / away_ | None→0.44 | REQUIRED |
| 13–14 | home_success_defense_allowed_5g / away_ | None→0.44 | REQUIRED |
| 15 | matchup_diff_off_epa_5g | None→0.0 | REQUIRED |
| 16 | matchup_diff_def_epa_allowed_5g | None→0.0 | REQUIRED |
| 17 | matchup_diff_success_rate_5g | None→0.0 | REQUIRED, DERIVED (see §4) |
| 18 | matchup_diff_pressure_generated_5g | None→0.0 | REQUIRED |
| 19 | matchup_diff_pressure_allowed_5g | None→0.0 | REQUIRED |
| 20 | matchup_diff_red_zone_td_rate_5g | None→0.0 | REQUIRED |

Non-efficiency REQUIRED context (not counted): game_id, home_team, away_team, matchup_season=2026, matchup_week, rest_days_home/away (default 7.0 → must be schedule-derived via existing `rest_days_from_schedule`).

**FORBID silent defaults:** any of #1–20 None/NaN/non-finite, or present only because the dataclass/`or` default (1.0/0.0/0.57/0.44) fired → ROW REJECT. Emitter must assert explicit finite values before calling the sim (pre-call gate; no sim code change).

Consumed-but-OUTSIDE minimum set → must be **None and recorded** in manifest (frozen-at-pin, as E1 t4768u): tendency_spread_signal / tendency_total_signal / tendency_proe_home/away; home/away_kav_{offense,defense,net}_5g, kav_as_of_week; personnel_edge_5g, sub_elasticity_5g, coach_aggression_5g, coach_pace_5g; all injury_nowcast_*; weather_*. Populating any = scope change → CoS.

## 4. Transforms (existing approved only)
- T1 team-game base: `nfl_dp_team_situational_weekly` (one row per team per PLAYED game; season, week, team): epa_per_play_offense, epa_per_play_defense_allowed, pass_rate, success rate off / def-allowed, pressure_rate_allowed/generated, red_zone_td_rate.
- T2 rolling 5g (ingest.py 33f2bf4e): `AVG(x) OVER (PARTITION BY team ORDER BY season, week ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)`, partition per season; byes produce no row → window = last ≤5 PLAYED games; `games_in_window_5` recorded. No opponent adjustment exists in this path — none to be added.
- T3 matchup row: home_* / away_* = team rolling values; diff_off_epa_5g = h.off − a.off; diff_def_epa_allowed_5g = a.def_allowed − h.def_allowed; diff_pressure_generated_5g = h − a; diff_pressure_allowed_5g = a − h; diff_red_zone_td_rate_5g per builder.
- T4 derived (nfl_matchup_features.py `matchup_pack_to_sim_input_kwargs`): matchup_diff_success_rate_5g = mean of available {(h_succ_off − a_succ_off), (a_succ_def − h_succ_def)}. E1 contract: BOTH terms required (a one-term mean = ROW REJECT).
- T5 offense/defense_index: existing `team_strength_from_record` (nfl_data.py): win_pct from W-L through W8 → off=clamp(0.90+0.22·wp, 0.82, 1.18), def=clamp(0.92+0.20·wp, 0.82, 1.20). Record must be computed from W1–W8 final results (ties per source rule, recorded). Malformed record → code returns 1.0 = silent default → ROW REJECT.
- **As-of binding of T3 (critical):** builder joins team rolling ON `h.week = s.week` (window includes CURRENT ROW). For W9 consumption the team rolling row used MUST be each team's latest row with week ≤ 8 (through-W8), never a week-9 row. A W9 matchup row populated from week-9 team rows = same-week leakage → WEEK REJECT. This is a consumption key, not a recipe change.

## 5. As-of / temporal cutoffs
- Inputs = 2026 W1–W8 only; as_of_ts (tz-aware UTC) ≤ emit_ts; emit_ts ∈ [2026-11-03 00:00, 2026-11-04 23:59 ET].
- through-W8 declared complete only when ALL 2026 W8 scheduled games are final and present in T1 (incl. MNF Nov 2) — DECISION 751dd63c.
- No W9+ play, no post-emit revision, no source row with ingest_ts > emit_ts.
- No 2025-prior substitution (backbone 4cd45f85 / epa_priors a4e3fa90) — denied for E1. No early-season market blend (W9 boost=0; market_blend=0 asserted).
- Naive/mixed-offset timestamps REJECT (consistent with F5 test).

## 6. Required coverage
- Slate: all 15 packaged W9 games (manifest game_ids, schedule d88ae734). Teams: the 30 slate teams must have complete fields; all 32 teams must have complete W1–W8 T1 coverage (needed for through-W8 completeness + W-L record; the 2 bye teams' data is not emitted but W8-completeness covers all games).
- Per team: games_in_window_5 = min(5, games played thru W8) and ≥5 expected at W9 (each team has played ≥7); <5 when ≥5 played → ROW REJECT.
- Field completeness: 20/20 required fields finite per row (100%); no threshold below 100%.
- Week scoring-admissible only if 15/15 rows ACCEPT.

## 7. Fail-closed rules
| Condition | Outcome |
|---|---|
| Any W8 game missing/not final in source | WEEK REJECT (through-W8 not complete) |
| Any W1–W7 game missing for a slate team | ROW REJECT those games' rows; and week not admissible |
| Any required field None/non-finite/default-fired | ROW REJECT |
| Week-9 rolling row consumed / as_of > emit_ts / 2025 prior used | WEEK REJECT |
| Source not Cursor DATA_READY + IMV ACCEPT | no emit (E1 stays FAIL_CLOSED) |
| Any ROW REJECT | week NOT scoring-admissible (O4=NO); rows may be sealed as diagnostic-labeled only |
| emit_ts outside Tue–Wed window | O4=NO; slips to W10 (Nov 10–11 ET) under same contract w/ W1–W9 |
Align: paper D3 (missing required field / future as_of rejects; no impute) and O4; honesty standard ebfcd85b (state MISSING, never fill).

## 8. E2 timing safeguard — RECORD ONLY (≠ CLEAR E2)
1. **emit_ts**: UTC ts of sealed IF forecast write; all inputs as_of ≤ emit_ts.
2. **snapshot_ts**: midweek DK totals captured_at, Tue–Wed window, captured_at ≥ emit_ts. A later market comparison only.
3. **close_ts**: last DK totals quote ts strictly < kickoff.
A post-forecast snapshot (2) or close (3) must NEVER be represented as information available at emit; neither may enter E1 inputs, calibration, or labels. E2 still needs separate CLEAR-B DK snap+close; Odds HOLD 70c56700 preserved.

## 9. Out of scope / HARD STOPS
Emit; E2; Odds; C10/Railway/DATABASE_URL; prod DB mutation; retune/weights/calibration change; new features; new hypothesis; scoring; holdout peek; merge/deploy (#662); register edits; KEI; CERT; Coming Soon OFF; paid data; messages. Need for unapproved fetch/credential → owner-blocked packet.

## 10. Does NOT authorize
Any emit retry. E1 retry requires: Cursor DATA_READY (sealed dataset+manifest per 751dd63c) + IMV ACCEPT of inputs against this contract + existing paper ec343df3 gates + new CoS CLEAR. Contract changes nothing in code, paper, or IMV grade.
