# t4643u INPUT-CONSUMPTION MATRIX — IMV C0–C7 / G1–G4

Eng correctness ≠ predictive improvement. Sealed 7c2d9625. Binding **062197c0**.
Verdict enum: `CONSUMED` | `READ+GATE` | `PROVENANCE_ONLY` | `GAP` | `MISSING` | `STALE_FALLBACK`

Oracle script: `services/model-service/tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py`
Seed **4643** · C1 sims 1200 · C2 builder `_simulate_one` (4000) / `_rest_days`.
Fixture sha256: `fixtures/FIXTURES.sha256`.

## Five completeness families (C0)

| family | IMV | verdict | SoT → file:line → flag | C3 pin | C1 oracle | C2 fallback / flags | repair |
|---|---|---|---|---|---|---|---|
| `current_weekly_depth_db` | **G1** | **GAP** | no `FROM nfl_dp_*` · `run_w8…:1078` `Does not read DATABASE_URL` · missing_doc warehouse | probe `f50ba2f07df9f92cba0ddf31fd5003f549d5e114eb3eddff0e245ef8f68c18ff` · no forecast SELECT | n/a (not CONSUMED) | refuse wire · `test_c3_g1_no_warehouse_select_in_forecast_path` | none — C3 · `T-G1-NO-SELECT` |
| `depth_sot_week` | **G2** | **READ+GATE** + **PROVENANCE_ONLY** + **GAP_SIM_VOLUME** | `_depth_meta` `:375-388` → pack write `:596-654` → artifact `depth_role=provenance_only` `:579` · **no** `NflGameInputs` depth field | W8 pack `550e1a8d3daef00ca963c91e30849ce368ec631df06302305c64faa69fab2e1d` week=8 as_of 2026-10-28 · 809/32 | n/a (C5: not CONSUMED) | EPA remains volume · `C2_sealed_restore_oracle.json` `6d303b90…` · `test_c2_g3_and_g2_sealed_restore_flags` · `test_c5_g2_depth_not_consumed_no_volume_fields` | labels only · `T-G2-NO-VOLUME` |
| `injury_paths_current` | baseline CONSUMED | **CONSUMED** into `impact_*` | `_injury_impacts` `:313-372` → `_simulate_one` `:426-432` → `injury_nowcast_impact_*` · means × `injury_conf` (`framework.py:311-341`) | W7 pack `0c29ceea500f34dd326e3b8879372fc6f2b6ea821ac72613ce4e35cadf013a97` designated n=153 | `C1_inj_impact_only.json` `ef31a571…` · field identity; means stay 0 | last designated week · no silent healthy · `C2_g3_last_designated.json` `092d685d…` | no invent · R1 confidence after CLEAR · `T-C1-INJ-FIELD` |
| W8 official report | **G3** | **MISSING** | `_injury_impacts` always `w8_official_report=MISSING` `:355` · `_simulate_one` flags `w8_official_injury_report` `:461` + `injury_as_of_week8` `:465-468` | none (do not invent) | n/a | `w8_official_injury_report` · `injury_as_of_week8` · 14/14 sealed restore · `C2_sealed_restore_oracle.json` | no invent · `T-G3-NO-INVENT` |
| `week_schedule_kickoffs` | baseline CONSUMED | **CONSUMED** | `_load_canonical_week` `:179-204` · `_rest_days` `:207-225` → `rest_days_*` `:419-420` · `rest_travel` (`framework.py:299-308`) | canonical `d88ae73440d3da87198ddb9d8986e0a19773cd3626215e495138907c44ff43fe` · 14 games | `C1_rest_home_extra.json` `1e5f6ce0…` → `rest_travel.margin_points` | rest None → 7.0 **and** flag `rest_days_*` · `C2_rest_home_missing.json` `e45d6073…` · helper `C2_rest_days_schedule.json` `fb14d488…` | none (C4 preserve) |
| `inseason_efficiency_current` | baseline CONSUMED | **CONSUMED** | `_build_current_strength` `:249-310` · `epa_to_strength_indices` → O/D `:415-418` · `base_efficiency` (`framework.py:280-297`) | W7 EPA `cb1fe8c5e0495c417af3dc70f83cf4c419c1c1761b2dd233bc8546ad3face2c2` · 32 teams week_through=7 | `C1_epa_home_boost.json` `2c2cc50b…` → `base_efficiency.margin_points` | refuse-to-sim if strength missing · `C2_epa_strength_missing.json` `43a19746…` · no silent 2025 prior | none (C4 preserve) |

C0 also requires season-engine §3 surfaces — see G4.

## G4 season vs game (C0 + C6)

| surface | game / research | season engine | verdict | handling |
|---|---|---|---|---|
| Depth | W8 pack 2026-10-28 `550e1a8d…` | W1 pack 2026-08-13 `21f202ec…` exclusive (`loaders.py:7-17,1653-1682`) | **STALE_FALLBACK** on season | **C6b DEFER + Needs-CLEAR** · `test_c6_g4_season_still_binds_w1_and_2025_prior` |
| Strength | W1–W7 EPA `cb1fe8c5…` | 2025 prior 2026-08-08 `4cd45f85…` or rolling (`loaders.py:19-25,1455`) | **STALE_FALLBACK** on season | **C6b DEFER + Needs-CLEAR** |
| Injury | W7 designated `0c29ceea…` | warehouse max_week=3 | **STALE_FALLBACK** if wired | do not wire |

## C1 fixture oracles (hashed)

| fixture | sha256 | perturbation | intended move | must not move |
|---|---|---|---|---|
| `C1_base.json` | `fc0f79f827b2cec46a2d54ba21b6badbc380b227142b4ecdc5ee52a0c13fb19e` | — | — | — |
| `C1_epa_home_boost.json` | `2c2cc50b6f2678693055a6a0026a78bb7499dd23a71e6f918ada43842dd55146` | offense_index_home 1.00→1.12 | base_efficiency / home WP | rest_days; injuries_depth means |
| `C1_rest_home_extra.json` | `1e5f6ce092581abbd2ed006549939b099d8bb72902e27176c3b220adeaae4fe0` | rest_days_home 7→10 | rest_travel | EPA indices; injuries_depth means |
| `C1_inj_impact_only.json` | `ef31a571c708b782b4aa883485bcfdb7971480ebfe63f0431113ea3544a53c1e` | impact_home=0.45 away=0.05, no confidence | impact field identity | injuries_depth.margin_points stay 0 |

## C2 fixture oracles (hashed)

| fixture | sha256 | remove / null | fallback that MUST fire | required flags |
|---|---|---|---|---|
| `C2_g3_last_designated.json` | `092d685dfbed9fbfc45d7a13817e81946458d617a5c59c0b42dbaa91171cc68e` | W8 official absent; overlay as_of 7/6 | last designated week; do not invent week 8 | `w8_official_injury_report` · `injury_as_of_week8` · `injury_as_of_week8_away` · `w8_official_report=MISSING` |
| `C2_sealed_restore_oracle.json` | `6d303b90339867cb744708fd894c84035c6b334cbc2d6ac41edef7a6e00b7103` | 14 sealed restore games | overlay `week7_or_latest_official_designations_only` | same G3 flags + `depth_role=provenance_only` · `odds_api=false` · `cert_candidate=0` |
| `C2_rest_home_missing.json` | `e45d6073180d37fcc1cc90edac85e3bc8e492c7d3724d2b1a93764c368b7d9c2` | rest_home = null | engine rest 7.0 | `rest_days_home` in missing; helper source `MISSING` |
| `C2_rest_days_schedule.json` | `fb14d4881c9b9cd13e18c877e865817fb8110a30ce1a9b422db1c35ce82301ef` | team with no prior kickoff | helper returns `(None, MISSING)` not silent 7.0 | present GB = 7.0 `schedule_kickoff_delta` |
| `C2_epa_strength_missing.json` | `43a19746bb2a557f0522cc56ea049d59b5620218522f4deb98ec4d470b9b7ae3` | strength = {} | SystemExit `MISSING current strength` | no silent 2025 prior pack |

Forbidden silent (all families): silent healthy · silent zero-as-official · silent W1-pack as W8 · silent warehouse skip-as-consumed · silent 7.0 as measured rest.

## C7

No MAE / CERT / invent-W8 / merge / Odds / F2 asserted as eng PASS.
This matrix is the WS-A sealed grading surface. Cursor does **not** self-grade `PASS_ENG_CONTRACT`.
