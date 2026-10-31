# t4621u CONSUME_PROOF — W8 forecast path vs five CLOSED checks

Ticket: t4621u
Authority: DECISION 095d17df · completeness sha8 **675e1cf7** (close tip `2f24c895`) · branch tip at paper `f03581fa`
CERT_CANDIDATE: 0
Label: RESEARCH_ENG
Path under proof: `scripts/nfl/run_w8_research_forecast_t4564u.py` (`main` → `_simulate_one` → `simulate_nfl_game`)
Not in scope: Exp D-R / #648 · Odds · F2 · deploy · publish · invent · holdouts

This paper proves **read / consume / miss** for the current W8 research forecast path against the five checks CLOSED at completeness `675e1cf7`. It does not re-emit a slate.

## Call graph (current W8 research forecast)

```
run_w8_research_forecast_t4564u.main
  ├─ _download nflverse parquets (depth_charts / injuries / stats_team_week)
  ├─ pd.read_parquet ×3
  ├─ _depth_meta + as_of gate (>= 2026-10-20)     → depth_sot_week READ+GATE
  ├─ _injury_impacts → compute_team_week_injury_severity
  │     → NflGameInputs.injury_nowcast_impact_* → simulate_nfl_game
  │                                             → injury_paths_current CONSUMED
  ├─ _build_current_strength → epa_to_strength_indices
  │     → NflGameInputs offense/defense indices → inseason_efficiency CONSUMED
  ├─ _load_canonical_week → _rest_days
  │     → slate + NflGameInputs.rest_days_*     → week_schedule_kickoffs CONSUMED
  ├─ _simulate_one  (no depth rows; no nfl_dp_* SELECT)
  ├─ _materialize_current_packs → audit_week_inputs (completeness write)
  └─ never railway run / SET TRANSACTION READ ONLY / nfl_dp_* SELECT
                                              → current_weekly_depth_db GAP
```

## CLOSED vs GAP per input

| check | completeness 675e1cf7 | forecast path | verdict |
|---|---|---|---|
| depth_sot_week | CLOSED pack W8 as_of 2026-10-28 · 809 rows / 32 teams | Reads nflverse `depth_charts_2026.parquet`; gates `as_of`; writes the CLOSED pack. **Does not pass depth rows into `NflGameInputs`.** `used_for=provenance_only_not_player_box_volume`. Team-sim volume is EPA. | **READ+GATE · GAP_SIM_VOLUME** |
| injury_paths_current | CLOSED W7 designated n=153 · W8 official MISSING | Reads injuries parquet → `_injury_impacts` → `compute_team_week_injury_severity` → `injury_nowcast_impact_home/away` → `simulate_nfl_game._build_totals_adjustments` | **CONSUMED** |
| current_weekly_depth_db | CLOSED via RO probe (warehouse W8 depth n=2907 / 32) | Exact miss: `Does not read DATABASE_URL` (repro docstring). `missing_doc` lists `DATABASE_URL / nfl_dp_* warehouse`. No `nfl_dp_depth_chart_weekly` / `nfl_dp_injuries` SELECT on this path. | **GAP** |
| week_schedule_kickoffs | CLOSED 14 canonical game_ids | `_load_canonical_week` requires 14 W8 rows; kickoffs drive rest; `game_id` + `kickoff_utc` enter the artifact | **CONSUMED** |
| inseason_efficiency_current | CLOSED W1–W7 nflverse EPA · 32 teams · prior_season null | `_build_current_strength` play-weighted W1–W7 → `epa_to_strength_indices` → O/D indices + EPA-per-play on `NflGameInputs` | **CONSUMED** |

## 1. File+line evidence

### depth_sot_week — READ+GATE · GAP_SIM_VOLUME

CLOSED artifact: `data/ops/nfl-t4605u-w8-pipeline-restore/current_inputs/nfl_depth_chart_2026_w8.json` (week=8, as_of 2026-10-28, snapshot `nfl-depth-2026-w8-20261028T060145Z`).

| step | file:line | what |
|---|---|---|
| download / read parquet | `scripts/nfl/run_w8_research_forecast_t4564u.py:67-70,791-798` | `depth_charts_2026.parquet` |
| meta | same `:375-388` | `used_for: provenance_only_not_player_box_volume`; `not_used: packaged nfl_depth_chart_2026_w1.json` |
| as_of gate | same `:809-811` | exit if snapshot date `< 2026-10-20` |
| pack write (completeness SoT) | same `:596-654,724-726,987-997` | writes the CLOSED W8 JSON; notes say team-sim volume is EPA-based |
| sim miss | same `:411-439` | `NflGameInputs(...)` has no depth / roster / player-box fields |
| artifact flag | same `:579` | `input_provenance.depth_role = "provenance_only"` |

Exact miss for **volume**: depth rows never reach `simulate_nfl_game`. Completeness can be CLOSED while the game mean is EPA-only.

### injury_paths_current — CONSUMED

CLOSED artifact: `…/current_inputs/nfl_injuries_2026_w7_designated.json` (week=7, designated_count=153, `w8_official_report=MISSING`).

| step | file:line | what |
|---|---|---|
| read parquet | `run_w8_research_forecast_t4564u.py:72-74,799,803` | `injuries_2026.parquet` |
| per-team latest designated week | same `:313-372` | filter `Out/Doubtful/Questionable` only; blank/practice-only excluded |
| severity | `services/model-service/src/services/nfl_injury_nowcast.py` (`compute_team_week_injury_severity`) | imported `:41` |
| into sim | `run_w8_research_forecast_t4564u.py:426-432` | `injury_nowcast_impact_home/away` |
| applied | `services/model-service/src/services/nfl_simulator.py:357-358,439` | totals adjustment uses those impacts |

W8 official report is **not invented**. Overlay is last official designations (see §2).

### current_weekly_depth_db — GAP

CLOSED by t4615u RO probe (`data/ops/nfl-t4615u-w8-depth-db-fresh-vm/depth_db_ro_probe.json`, sha8 `f50ba2f0`): `nfl_dp_depth_chart_weekly` W8 n=2907 / 32 teams.

Exact miss on the forecast path:

| miss | file:line |
|---|---|
| repro: "Does not read DATABASE_URL" | `run_w8_research_forecast_t4564u.py:1078` |
| slate missing list includes warehouse | same `:848-855` (`DATABASE_URL / nfl_dp_* warehouse on this VM`) |
| per-game missing includes `nfl_dp_team_rolling_features_weekly` | same `:461-463` |
| `database_url_present` recorded false on the landed restore | `…/t4605u-restore-…/input_as_of.json` |
| completeness close was a **separate** `railway run` probe, not this script | `scripts/nfl/probe_w8_depth_db_ro_t4615u.py` |

No `nfl_dp_*` SELECT is executed by `run_w8_research_forecast_t4564u.py`. Warehouse CLOSED ≠ forecast consumed.

### week_schedule_kickoffs — CONSUMED

CLOSED slate: 14 ids in completeness `675e1cf7` (`2026-W08-CAR@GB` … `2026-W08-CHI@SEA`).

| step | file:line | what |
|---|---|---|
| SoT file | `services/model-service/src/services/nfl_season_engine/data/nfl-canonical-schedule-2026.json` | constant `CANONICAL` `:82-85` |
| load week 8 | `run_w8_research_forecast_t4564u.py:179-204,804-806` | require exactly 14 games |
| rest | same `:207-225,864-865` | `schedule_kickoff_delta` from prior kickoff |
| artifact | same `:502-507,526-534` | `game_id` + `kickoff_utc` + pre-kickoff lead |

### inseason_efficiency_current — CONSUMED

CLOSED artifact: `…/current_inputs/nfl_team_efficiency_backbone_2026_inseason_w7.json` (week_through=7, 32 teams, `prior_season=null`, source `nflverse_stats_team_week_2026`).

| step | file:line | what |
|---|---|---|
| read parquet | `run_w8_research_forecast_t4564u.py:76-79,800` | `stats_team_week_2026.parquet` |
| play-weighted W1–W7 | same `:249-310` | passing+rushing EPA / plays; `epa_to_strength_indices` |
| gate | same `:814-817` | team-week max ≥ 7 and 32 teams |
| into sim | same `:415-418,433-436` | O/D indices + EPA-per-play on `NflGameInputs` |
| conversion | `services/model-service/src/services/nfl_season_engine/efficiency_backbone.py` (`epa_to_strength_indices`) | imported `:43` |

Not the packaged 2025-prior backbone (`as_of 2026-08-08`). See §3.

## 2. Official injury coverage

| fact | value | source |
|---|---|---|
| Designated week (pack / completeness) | **7** | completeness 675e1cf7 `injury_paths_current.latest_official_week`; pack week=7 |
| Designated count | **153** | same; filter Out / Doubtful / Questionable |
| W7 report rows (incl. undesignated) | 350 | restore `input_as_of.json` |
| W8 official Wednesday report | **MISSING** | pack `w8_official_report`; every game `missing_inputs` includes `w8_official_injury_report` and `injury_as_of_week8` |
| Parquet max week | 8 | restore `input_as_of.injuries.max_week=8` — week 8 rows exist but have **no designations** (empty-status stub; not treated as official) |
| Silent healthy | forbidden | `_injury_impacts` excludes blank / practice-only |

**W8 MISSING impact (landed restore slate `t4605u-restore-20261028T134541Z`):**

- All **14 / 14** games flag `w8_official_injury_report` + `injury_as_of_week8` (+ away twin).
- Overlay uses **latest week with designations**, not week 8 zeros.
- Per-side as_of on that slate:
  - week **7**: 23 of 28 team-sides
  - week **6**: BUF, JAX, LAC, WAS (4 sides)
  - week **5**: CIN (TEN@CIN home)
- Impact scores still enter `simulate_nfl_game` totals adjustments. They are **W7-or-earlier official**, not a W8 report.
- Warehouse `nfl_dp_injuries` (t4615u probe) is **max_week=3** — older than the research overlay. Not used by this path (GAP above).

## 3. Game-level vs season / strength-selection SoT

| surface | SoT (named) | W8-relevant vintage | conflict vs CLOSED 675e1cf7 |
|---|---|---|---|
| **Game-level research forecast** (this path) | nflverse `stats_team_week_2026` → `epa_to_strength_indices` (play-weighted W1–W7) | as_of 2026-10-28 / week_through 7 | Matches `inseason_efficiency_current`. Does **not** use warehouse rolling. |
| **Season engine strengths** | 1) DB `nfl_dp_team_rolling_features_weekly` via `_load_team_strength_priors` 2) packaged `nfl_team_efficiency_backbone_2026.json` / `nfl_team_epa_priors_2026.json` 3) league-avg placeholder | packaged backbone: **prior_season=2025, as_of 2026-08-08** | **STALE vs inseason W7.** Game-level restore lists `warehouse_rolling=MISSING` and `nfl_dp_team_rolling_features_weekly` on every game. |
| **Game-level depth** | nflverse latest snapshot → W8 pack (completeness SoT) | as_of 2026-10-28, week=8 | Read for gate/provenance only. Not player-box volume. |
| **Season engine depth** | **Packaged `nfl_depth_chart_2026_w1.json` is exclusive player→team SoT when present**; `nfl_dp_depth_chart_weekly` / official **ignored** (`loaders.py:7-17,1653-1682`) | week=1, as_of **2026-08-13** | **STALE / CONFLICT.** Warehouse now has W8 weekly depth (2907 / 32). Season engine will skip it while the W1 pack exists. Research W8 pack is **not** the file `_PACKAGED_DEPTH_FILES` points at. |
| **Game-level injury** | nflverse injuries, latest designated week (W7 pack) | designated week 7; W8 official MISSING | Consumed as nowcast impact. |
| **Season / nowcast DB** | `nfl_dp_injuries` (`nfl_injury_nowcast.fetch_*`) | warehouse max_week **3** (t4615u probe) | **STALE vs W7 designated pack.** Game-level does not read it. |
| **Game-level schedule** | `nfl-canonical-schedule-2026.json` | 14 W8 games + `kickoff_utc` | Consumed (slate + rest). |
| **Season engine schedule** | DB `nfl_dp_schedules` else packaged `nfl_regular_schedule_2026.json` (`loaders.py:2-5,413-452,1413-1453`) | `ScheduledGame` has no kickoff field | Different file / no rest-from-kickoff on this loader. |

**Conflicting outputs if both surfaces were published (they are not; F2 frozen, CERT=0):**

1. Season player identities = W1 camp pack (2026-08-13). Research completeness depth = W8 nflverse (2026-10-28). Warehouse weekly = W8. Three books; season engine binds the oldest.
2. Season cold-start strength = 2025 prior (2026-08-08). Research game means = 2026 W1–W7 EPA. Same `epa_to_strength_indices` helper, different vintage.
3. Injury nowcast from warehouse would be W3; research overlay is W7 designated. W8 official still MISSING on both.
4. Game-level totals omit warehouse KAV / rolling features (honest MISSING). Season engine prefers those tables when a session exists.

No numbers invented to reconcile these. No second slate emitted.

## 4. What this does **not** claim

- Not a new forecast emit. Landed W8 numbers remain the t4605u restore (`8e49bfe7` / run `nfl-w8-2026-t4605u-restore-20261028T134541Z`).
- Not CERT. Not publish. Not F2. Not Odds.
- `current_weekly_depth_db` CLOSED (access) ≠ consumed by the forecast path.
- `depth_sot_week` CLOSED ≠ player-volume input to `simulate_nfl_game`.
- Exp D-R / #648 untouched.

## CLOSED vs remaining (consume, not access)

| check | consume verdict |
|---|---|
| depth_sot_week | READ+GATE · **GAP_SIM_VOLUME** |
| injury_paths_current | **CONSUMED** (W7 designated; W8 official MISSING) |
| current_weekly_depth_db | **GAP** (warehouse not read by forecast) |
| week_schedule_kickoffs | **CONSUMED** |
| inseason_efficiency_current | **CONSUMED** |

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen
No Odds · no merge · no deploy · no invent · no Exp D-R
