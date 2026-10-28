# t4643u WS-A CONTRACT — bound to IMV C0–C7 / G1–G4

Authority: DECISION **098da1dd** · IMV criteria **062197c0** (BINDING)
Sealed: CONSUME_PROOF **7c2d9625** / **0be23ede** · completeness **675e1cf7**
Path under proof: `scripts/nfl/run_w8_research_forecast_t4564u.py` → `_simulate_one` → `simulate_nfl_game`
CERT=0 · Eng correctness ≠ predictive improvement · C7 clean

Verdict enum (IMV): `CONSUMED` | `READ+GATE` | `PROVENANCE_ONLY` | `GAP` | `MISSING` | `STALE_FALLBACK`

## C0 — CONTRACT COMPLETENESS

| completeness family (675e1cf7) | IMV GAP / baseline | verdict | CLOSED access ≠ CONSUMED? |
|---|---|---|---|
| `current_weekly_depth_db` | **G1** | **GAP** | yes — warehouse CLOSED, no SELECT into forecast |
| `depth_sot_week` | **G2** | **READ+GATE** + **PROVENANCE_ONLY** + **GAP_SIM_VOLUME** | not labeled CONSUMED |
| `injury_paths_current` | baseline CONSUMED; **G3** official W8 | **CONSUMED** (designated overlay → `impact_*`) · official W8 **MISSING** | — |
| `week_schedule_kickoffs` | baseline CONSUMED | **CONSUMED** | — |
| `inseason_efficiency_current` | baseline CONSUMED | **CONSUMED** | — |

Season-engine §3 surfaces (required by C0):

| conflict | game / research | season engine | handling |
|---|---|---|---|
| Depth vintage | W8 nflverse pack as_of 2026-10-28 sha256 `550e1a8d…` | packaged W1 as_of 2026-08-13 sha256 `21f202ec…` | **G4** · DEFER + Needs-CLEAR (C6b) |
| Strength vintage | W1–W7 EPA sha256 `cb1fe8c5…` | 2025 prior as_of 2026-08-08 sha256 `4cd45f85…` or rolling DB | **G4** · DEFER + Needs-CLEAR |
| Injury vintage | designated W7 n=153 sha256 `0c29ceea…` | warehouse `nfl_dp_injuries` max_week=3 | **G4** · do not wire W3 |

C0 PASS condition: no family omitted; warehouse not labeled CONSUMED.

## C1 — PERTURBATION → INTENDED COMPONENT

Hashed fixtures: `fixtures/C1_*.json` (sha256 in `FIXTURES.sha256`).
Oracle script: `tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py` · seed **4643** · sims 1200.

| id | labeled | fixture pair | declared component | must NOT move | oracle |
|---|---|---|---|---|---|
| C1-EPA | CONSUMED `inseason_efficiency_current` | `C1_base` `fc0f79f8…` → `C1_epa_home_boost` `2c2cc50b…` | `base_efficiency.margin_points` + `mean_home_points` | `rest_days_*`; `injuries_depth.margin_points` | home offense 1.00→1.12 raises home WP / lowers spread |
| C1-REST | CONSUMED `week_schedule_kickoffs` | `C1_base` → `C1_rest_home_extra` `1e5f6ce0…` | `rest_travel.margin_points` | `injuries_depth.*`; EPA indices | rest 7/7 → 10/7 raises home WP |
| C1-INJ-FIELD | CONSUMED `injury_paths_current` | `C1_base` → `C1_inj_impact_only` `ef31a571…` | `diagnostics.injury_nowcast.home_impact` identity | `injuries_depth.margin_points` stay **0** (conf=0) | impact fields set; **means unchanged** |
| C1-DEPTH | G2 not CONSUMED | n/a until rows reach sim | — | — | C5: cannot claim CONSUMED |
| C1-DB | G1 not CONSUMED | n/a until SELECT | — | — | C3: GAP |

New exact miss (erratum-eligible, does not reopen 7c2d9625): designated overlay is CONSUMED into `impact_*` but **not** into `injuries_depth` mean points unless `injury_nowcast_confidence_*` is set. W8 builder does not set confidence.

## C2 — MISSING → FALLBACK + FLAG

| family | fallback if missing / irrelevant | required flags | forbidden silent | fixture oracle |
|---|---|---|---|---|
| G3 W8 official | last week **with designations** (W7/6/5); not week-8 empty stubs | `w8_official_injury_report` · `injury_as_of_week8` · pack `w8_official_report=MISSING` | silent healthy; silent zero-as-official; invent W8 rows | `C2_g3_last_designated.json` `092d685d…` + sealed 14/14 `C2_sealed_restore_oracle.json` `6d303b90…` |
| G2 depth | provenance-only; EPA remains volume | `depth_role=provenance_only` · `used_for=provenance_only_not_player_box_volume` | silent W1-pack as W8; claim CONSUMED | sealed restore + `test_c5_g2_depth_not_consumed_no_volume_fields` |
| G1 warehouse | refuse SELECT; completeness probe stays separate | `DATABASE_URL / nfl_dp_* warehouse` in missing_doc; `Does not read DATABASE_URL` | silent warehouse skip-as-consumed; wire-because-available | `test_c3_g1_no_warehouse_select_in_forecast_path` |
| schedule kickoff | rest `MISSING` → builder uses 7.0 **and** flags `rest_days_*` | `rest_days_home` / `rest_days_away` in missing_inputs when None | silent 7.0 as measured rest | `C2_rest_home_missing.json` `e45d6073…` · helper `C2_rest_days_schedule.json` `fb14d488…` |
| EPA | refuse-to-sim if strength missing | SystemExit `MISSING current strength` | silent 2025 prior pack | `C2_epa_strength_missing.json` `43a19746…` |

## C3 — AUTHORITY / VINTAGE PIN

| input | SoT | as_of / week | coverage | sha256 |
|---|---|---|---|---|
| depth_sot READ+GATE | `nfl_depth_chart_2026_w8.json` | 2026-10-28 / week 8 | 809 rows / 32 teams | `550e1a8d3daef00ca963c91e30849ce368ec631df06302305c64faa69fab2e1d` |
| injury CONSUMED | `nfl_injuries_2026_w7_designated.json` | 2026-10-28 / designated week **7** | 153 designated / 350 report rows | `0c29ceea500f34dd326e3b8879372fc6f2b6ea821ac72613ce4e35cadf013a97` |
| EPA CONSUMED | `nfl_team_efficiency_backbone_2026_inseason_w7.json` | 2026-10-28 / week_through 7 | 32 teams · prior_season null | `cb1fe8c5e0495c417af3dc70f83cf4c419c1c1761b2dd233bc8546ad3face2c2` |
| schedule CONSUMED | `nfl-canonical-schedule-2026.json` | 14 W8 games | 14/14 | `d88ae73440d3da87198ddb9d8986e0a19773cd3626215e495138907c44ff43fe` |
| warehouse G1 | RO probe only | W8 weekly n=2907 **flat w1–w8**; injuries max_week=3 | access CLOSED | probe `f50ba2f07df9f92cba0ddf31fd5003f549d5e114eb3eddff0e245ef8f68c18ff` · **GAP until SELECT + C1/C2** |

Wire-because-available: **RETURN** (098da1dd). See `WAREHOUSE_AUTHORITY.md`.

## C4 — NO REGRESSION ON ALREADY-CONSUMED

Repairs in this packet do **not** change `_simulate_one` field wiring for EPA, rest, or designated impact.
Tests C1-EPA, C1-REST, C1-INJ-FIELD, C2 injury flags must stay green.

## C5 — ROLE LABEL INTEGRITY

- G2 = `READ+GATE` + `PROVENANCE_ONLY` + `GAP_SIM_VOLUME`. **Not CONSUMED.**
- G1 = `GAP`. **Not CONSUMED.**
- Completeness CLOSED on warehouse/depth does not appear as CONSUMED in this contract or PR consume table.

## C6 — SEASON vs GAME SoT

Named (7c2d9625 §3):
1. Season depth exclusive W1 pack vs research/warehouse W8
2. Season strength 2025 prior / rolling vs research W1–W7
3. Warehouse injuries W3 vs research W7 designated

Handling: **(b) DEFER + Needs-CLEAR** for season-engine `_PACKAGED_DEPTH_FILES` / prior backbone / DB preference.
Game-level W8 research path remains authoritative for this emit (canonical schedule + nflverse W7/W8 packs). Season loader still binds conflicting packs — flagged, not silently claimed as one SoT.

## C7 — HARD NON-CLAIMS

This packet does **not** assert as eng PASS: MAE, market beat, nested G34, Exp A/D-R, CERT, fireable, publish, F2, Coming Soon OFF, invented W8 official injury, merge, deploy, Odds.

PASS_ENG_CONTRACT (if IMV grades later) ≠ CERT ≠ fireable slate.
