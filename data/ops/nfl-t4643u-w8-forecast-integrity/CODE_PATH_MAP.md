# t4643u CODE_PATH_MAP — W8 forecast integrity (WS-A P0)

Ticket: t4643u · Authority DECISION **098da1dd** · IMV **062197c0** BINDING
Sealed start: CONSUME_PROOF **7c2d9625** / **0be23ede** tip `70303058` (do not redo as discovery)
CERT_CANDIDATE: 0 · NFL NO-GO · no Odds · no F2 · #648 / G34 / Exp D-R untouched
Target: IMV C0–C7 and G1–G4 exactly. See `C0_C7_CONTRACT.md`.

This map names **which inputs move which numbers** on the two live engines.
“Read into a struct” is not enough — see effect column.

## Two engines (same spine rule, different SoT today)

| engine | entry | outputs | used by W8 research emit? |
|---|---|---|---|
| **Game forecast** | `simulate_nfl_game` (`nfl_simulator.py:513`) | spread / total / WP | **YES** — `run_w8_research_forecast_t4564u.py:_simulate_one` |
| **Season simulation** | `simulate_one_season_path` → `simulate_full_season` (`season_sim.py:127,333`) | path wins + player boxes → season totals / futures | **NO** — W8 research script never calls it |

Production ad-hoc HTTP also calls `simulate_nfl_game` (`routes/nfl.py:4854-4898`) with **overlays_off** and packaged-EPA strength (`resolve_adhoc_simulation_strength`). That is a third caller, not the W8 research emit.

```
AUTHORITATIVE INPUTS (claimed)
  schedule · injuries · depth · EPA · team strengths
        │
        ├─ W8 RESEARCH GAME PATH ────────────────────────────┐
        │  run_w8_research_forecast_t4564u.main              │
        │    nflverse parquets + canonical schedule          │
        │    → NflGameInputs → simulate_nfl_game             │
        │    → 14 game JSON + slate_table                    │
        │                                                    │
        └─ SEASON ENGINE PATH ───────────────────────────────┤
             load_universe_from_db                           │
               packaged W1 depth (exclusive)                 │
               rolling DB or packaged 2025-prior strength    │
               nfl_dp_schedules or packaged REG wall-chart   │
             → simulate_one_season_path                      │
               depth → usage shares (volume)                 │
               strengths → script / WP / boxes               │
               packaged injury_paths (not nflverse W7)       │
             → season totals / player futures                │
```

## Game-forecast effect table (`simulate_nfl_game`)

Decomposition: `compute_nfl_projection_decomposition` (`nfl_handicapping_framework.py:218`).
Totals overlay: `_build_totals_adjustments` (`nfl_simulator.py:345`).

| input | W8 research builder | reaches `NflGameInputs`? | **affects spread / WP / total?** |
|---|---|---|---|
| **EPA / team strengths** (O/D indices + EPA/play) | `_build_current_strength` → `epa_to_strength_indices` (`run_…:249-310,415-418,433-436`) | YES | **YES — primary mean.** `off_def_home/away` → `base_margin_points` / `base_total_points` (`framework.py:280-297`). |
| **Schedule kickoffs / rest** | `_load_canonical_week` + `_rest_days` (`:179-225,804-806,864-865`) | YES (`rest_days_*`; default 7.0 if MISSING) | **YES.** `rest_delta` → margin/total (`framework.py:299-308`); short-rest flag (`:344-350`). |
| **Injury designated rows** | `_injury_impacts` → `compute_team_week_injury_severity` (`:313-372,426-432`) | `impact_*` YES; **`confidence_*` NO; multipliers NO** | **Means: no-op.** `injuries_depth` points × `injury_conf` (`framework.py:311-341`). Missing confidence → 0 mean points. **StDev leakage:** `error_regime` uses raw `injury_impact` without confidence (`framework.py:837-861`) and can change MC spread/WP slightly. Severity helper returns no confidence (`nfl_injury_nowcast.py:404-441`). |
| **Depth chart rows** | `_depth_meta` + as_of gate + pack write (`:375-388,809-811,596-654`) | **NO** — no depth field on `NflGameInputs` | **NO.** Provenance / completeness only (`used_for=provenance_only_not_player_box_volume`). |
| **Warehouse `nfl_dp_*`** | none | **NO** | **NO.** Exact miss sealed in 7c2d9625 (`run_…:1078`). |
| Weather / travel / KAV / rolling 5g / market lines | explicitly False / MISSING | weather/travel False; KAV unset; no Odds | **NO** (honest MISSING). |

Reproducible: same `run_id:game_id` seed → identical markets (restore slate asserted `deterministic_ok=True`).

## Season-simulation effect table

| input | loader SoT | **affects season path?** |
|---|---|---|
| **Depth / roster roles** | Packaged `nfl_depth_chart_2026_w1.json` is **exclusive** player→team SoT when present (`loaders.py:7-17,1653-1682`). Warehouse weekly/official **skipped**. | **YES — player volume.** `allocate_game_usage` uses role shares (`player_usage.py:1-18,76+`). Weekly role volatility (`season_sim.py:186-191`). |
| **Team strengths** | `_load_team_strength_priors` = `nfl_dp_team_rolling_features_weekly` blended, else packaged backbone **2025 prior as_of 2026-08-08** (`loaders.py:19-25,1455`; `tasks.py` priors). | **YES — script / expected points / WP** (`game_script.py` + `team_strength.expected_team_points`). Evolve after each game (`season_sim.py` Layer 1). |
| **Schedule** | `nfl_dp_schedules` else `nfl_regular_schedule_2026.json`. `ScheduledGame` has **no kickoff** (`loaders.py:413-452,1413-1453`). | **YES — which games exist.** Rest-from-kickoff is **not** on this loader. |
| **Injury paths** | `universe.packaged_injury_paths` / `apply_injury_paths_for_week` (`season_sim.py:145-209`, `injury_paths.py`). Not the W7 nflverse designated pack. | **YES if paths present** — usage reallocation + offense_index delta. |
| **W8 nflverse EPA pack** | not loaded here | **NO** unless someone rebuilds priors from it. |
| **W8 research depth pack** | not `_PACKAGED_DEPTH_FILES` | **NO.** Season engine will keep W1 camp pack. |

## Provenance / flag consistency (current W8 research artifacts)

Honest flags already on the restore slate (`t4605u-restore-20261028T134541Z`):

- `injury_overlay=week7_or_latest_official_designations_only`
- `depth_role=provenance_only`
- every game `missing_inputs` includes `w8_official_injury_report`, `injury_as_of_week8`, `nfl_dp_team_rolling_features_weekly`
- `cert_candidate=0`, `odds_api=false`

Inconsistency to repair (not a new discovery — consequence of 7c2d9625 + engine math):

- Overlay is labeled CONSUMED, but **without confidence the injury term is a silent zero** on spread/total. Flag says overlay; mean does not move.

## What is *not* claimed

- Not a new slate emit. Not CERT. Not warehouse-into-prod.
- Nested G34 / Exp D-R / #648 untouched.
