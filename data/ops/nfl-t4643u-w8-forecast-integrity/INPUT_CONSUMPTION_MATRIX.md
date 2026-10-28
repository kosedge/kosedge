# t4643u INPUT-CONSUMPTION MATRIX — IMV C0–C7 / G1–G4

Eng correctness ≠ predictive improvement. Sealed 7c2d9625. Binding 062197c0.

Verdict: `CONSUMED` | `READ+GATE` | `PROVENANCE_ONLY` | `GAP` | `MISSING` | `STALE_FALLBACK`

## Five completeness families (C0)

| family | IMV | verdict | SoT pin (C3) | C1 component | C2 fallback / flags |
|---|---|---|---|---|---|
| `current_weekly_depth_db` | **G1** | **GAP** | probe `f50ba2f0` · no forecast SELECT | n/a until SELECT | refuse wire · `Does not read DATABASE_URL` · missing_doc warehouse |
| `depth_sot_week` | **G2** | **READ+GATE** + **PROVENANCE_ONLY** + **GAP_SIM_VOLUME** | W8 pack `550e1a8d` week=8 as_of 2026-10-28 · 809/32 | n/a (not CONSUMED) | EPA volume · `depth_role=provenance_only` |
| `injury_paths_current` | baseline CONSUMED | **CONSUMED** into `impact_*` | W7 pack `0c29ceea` designated n=153 | field identity `injury_nowcast_impact_*` | last designated week · no silent healthy |
| W8 official report | **G3** | **MISSING** | none | n/a | `w8_official_injury_report` · `injury_as_of_week8` · do not invent |
| `week_schedule_kickoffs` | baseline CONSUMED | **CONSUMED** | canonical `d88ae734` · 14 games | `rest_travel.margin_points` + slate | rest MISSING → 7.0 **flagged** |
| `inseason_efficiency_current` | baseline CONSUMED | **CONSUMED** | W7 EPA `cb1fe8c5` · 32 teams week_through=7 | `base_efficiency.margin_points` | refuse-to-sim if <32 or week<7 |

## G4 season vs game (C0 + C6)

| surface | game / research | season engine | verdict | handling |
|---|---|---|---|---|
| Depth | W8 pack 2026-10-28 | W1 pack 2026-08-13 `21f202ec` exclusive | **STALE_FALLBACK** on season | C6b DEFER + Needs-CLEAR |
| Strength | W1–W7 EPA `cb1fe8c5` | 2025 prior 2026-08-08 `4cd45f85` or rolling | **STALE_FALLBACK** on season | C6b DEFER + Needs-CLEAR |
| Injury | W7 designated `0c29ceea` | warehouse max_week=3 | **STALE_FALLBACK** if wired | do not wire |

## C1 fixture oracles (hashed)

| fixture | sha256 (see FIXTURES.sha256) | perturbation | intended move | must not move |
|---|---|---|---|---|
| `C1_base.json` | computed at land | — | — | — |
| `C1_epa_home_boost.json` | | offense_index_home 1.00→1.12 | base_efficiency / home WP | rest_days; injuries_depth means |
| `C1_rest_home_extra.json` | | rest_days_home 7→10 | rest_travel | EPA indices; injuries_depth means |
| `C1_inj_impact_only.json` | | impact_home=0.45 away=0.05, no confidence | impact field identity | injuries_depth.margin_points stay 0 |

## C7

No MAE / CERT / invent-W8 / merge / Odds / F2 asserted as eng PASS.
