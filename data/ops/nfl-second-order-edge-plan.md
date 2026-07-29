# NFL Second-Order Edge — Implementation Plan

**Branch:** `nfl-second-order-edge` (from `nfl-kav-sharpen`)  
**Constraint:** Extend `nfl_simulator` / `nfl_handicapping_framework` / player engine; preserve `nfl-v1.5-matchup-sim`, leakage lags, champion/challenger.

## Modules (A–H)

| ID | Module | Phase | Status target |
|----|--------|-------|---------------|
| A | Coach aggression latents + conditional play-calling | 3 | Ship this session |
| B | Personnel efficiency + substitution elasticity | 2 | Ship this session |
| C | Org belief / role elasticity → player engine | 4 | Stub / later |
| D | Error-regime meta-calibration | 5 | Later |
| E | Info velocity / injury practice | 6 | Later |
| F | Same-game correlations → portfolio optimizer | 7 | Extend existing optimizer later |
| G | Scheme-fit interactions | 8 | Later |
| H | Enhanced weather + circadian/load | 1 skeleton + later interactions | VC skeleton this session |

## Phases

### Phase 1 — Data ingestion skeletons
- nflverse: ensure pbp/participation/draft/rosters paths; add PBP columns `offense_personnel`, `defense_personnel`, `wp`, `vegas_wp`, `fixed_drive`, `series` (from raw; re-normalize to backfill).
- Visual Crossing weather client + day cache (`VISUAL_CROSSING_API_KEY`); graceful fallback to Open-Meteo.
- OTC / Spotrac clients env-gated (`OTC_API_KEY` / `SPOTRAC_*`); cache only.
- PFF skeleton: export-path + rate-limited fetch stub; `source=pff_*` tags; never burn Odds credits.

### Phase 2 — Personnel + substitution
- Tables: `nfl_dp_personnel_efficiency_weekly`, `nfl_dp_substitution_elasticity_weekly`.
- Materializers from PBP (+ snaps if present); **strict week−1 lag** for pre-game joins.
- Matchup pack columns + framework factor `personnel_efficiency`.

### Phase 3 — Coach aggression
- Table: `nfl_coach_aggression_weekly`.
- Latents: 4th-down go rate residual, early-down PROE, no-huddle rate, score-state pass aggression.
- Framework factor `coach_aggression` (margin + mild total via pace).

### Phase 4+ (later sessions)
- Org belief elasticity → `nfl_player_projection_engine`.
- Error regimes, practice/injury velocity, SGP corr matrix, scheme-fit, weather×load interactions.

## Migrations
- `043_nfl_second_order_edge.sql` — PBP columns, external cache, personnel/sub/coach weekly, matchup ALTER.

## Env vars
| Var | Purpose |
|-----|---------|
| `VISUAL_CROSSING_API_KEY` | Weather (1000/day free; cached) |
| `NFL_VC_WEATHER_ENABLED` | Prefer VC over Open-Meteo when keyed |
| `OTC_ENABLED` / `OTC_API_KEY` | OverTheCap contracts |
| `SPOTRAC_ENABLED` / `SPOTRAC_API_KEY` | Spotrac (optional) |
| `PFF_ENABLED` / `PFF_EXPORT_DIR` / `PFF_USERNAME` / `PFF_PASSWORD` | PFF skeleton |
| `NFL_FRAMEWORK_PERSONNEL_ENABLED` | Factor toggle (default true) |
| `NFL_FRAMEWORK_COACH_AGGRESSION_ENABLED` | Factor toggle (default true) |
| `NFL_FRAMEWORK_PERSONNEL_*` / `NFL_FRAMEWORK_COACH_*` | Weights / clamps |

## Risks
1. **Coverage penalty** — new factors `available=False` until materializers run; disable via env for live boards pre-backfill.
2. **PBP re-normalize** — personnel/wp columns NULL until `--normalize-pbp-from-raw --replace-normalized`.
3. **VC quota** — hard day cache; never call without key.
4. **Leakage** — all weekly features join `as_of_week = game.week - 1`; assert helper shared with KAV pattern.
5. **Unrelated WIP** — paper-track files stashed off this branch.

## Dry-run notes
1. Apply `043_nfl_second_order_edge.sql`.
2. `python -m data_platform_nfl.cli --normalize-pbp-from-raw --replace-normalized --seasons=2023,2024,2025`.
3. `--materialize-personnel-efficiency --materialize-coach-aggression --seasons=...`.
4. Sim with `NFL_FRAMEWORK_PERSONNEL_ENABLED=true` and inspect `decomposition.factor_contributions`.
5. Without keys, VC/OTC/PFF return empty + `source=unavailable` — sim must not crash.

## Wiring pattern (additive)
Config → kwargs on `compute_nfl_projection_decomposition` → contribution dict → sum into predicted margin/total → `NflGameInputs` fields → matchup pack / fetchers. **Do not** touch MC loop.
