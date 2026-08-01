# MLB Statcast stuff_proxy densify (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `d1df6816-b65c-496c-9af9-ff51a2daddce` (`run_mlb_sp_talent_ablation` T0/T3)  
**PR:** [#58](https://github.com/kosedge/kosedge/pull/58)  
**HFA:** 1.025 held; matchup ON; wind-dir ON; bullpen role **off**; lineup timing **off**  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Artifact:** `statcast_stuff_2026-08-01.json`

## What was built

### `stuff_proxy` mode (flag only)
- Baseball Savant pitch-level CSV → local cache → compact `pitcher_asof_index.json`
- As-of join: pitches with `game_date ≤ game_date − 1` only (leakage-safe)
- Metrics → quality: whiff%, chase%, zone%, avg EV against, barrel%
- Thin sample (`<200` pitches) → K-BB shape fallback (never ERA)
- Ablation config **T3** (`mlb-v1-pa-sim-talent-t3`)
- Pitch-sim remains gated off (`MLB_ENABLE_PITCH_SIM=false`)

### Credit / rate notes
- Source: public Baseball Savant `statcast_search/csv` (not Odds API)
- Bulky CSV chunks gitignored; compact as-of index shipped in model-service image

## Intersection-n (n = 476)

| Config | ML CLV | RL CLV | Total CLV | WF Brier | MAE | Leak |
|--------|-------:|-------:|----------:|---------:|----:|-----:|
| T0 era_whip (as-of) | **+0.00426** | +0.025 | +0.002 | **0.24999** | **3.478** | **0** |
| T3 stuff_proxy | +0.00414 | **+0.051** | +0.002 | 0.25114 | 3.484 | **0** |

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** |
| Intersection ML CLV | ≥ +0.010 (stretch +0.015) | **FAIL** (T3 +0.00414) |
| Beat T0 on ML meaningfully | clear lift | **FAIL** (T3 −0.00012 vs T0) |
| Densify base Brier | ≤ 0.248 | **FAIL** (T3 worse than T0) |

## Decision

**Ship nothing from T3.** Production default stays:

- `starter_quality_mode = era_whip` (S0)
- `bullpen_role_quality_mode = off`
- HFA 1.025, matchup ON, wind-dir ON

### Keep in codebase (infrastructure, not default flip)

1. `stuff_proxy` + Savant as-of cache/index + T3 ablation job  
2. Prewarm script `scripts/mlb/build_statcast_stuff_cache.py`  
3. Unit tests for aggregate / as-of cutoff / quality map  

### Why not ship T3?

Intersection ML moves **down** vs T0 by ~0.00012 — noise band of prior S0/T0–T2 (+0.004). RL CLV rises but total CLV flat; Brier worsens. No subscription unlock.

## Next levers (honest)

Season-to-date Statcast aggregates as another `starter_quality` rewrite are **not** the missing CLV. Still ~**+0.004** intersection ML.

Candidates with different information structure:

1. True late-info projection stamps (as-of lineup/SP snapshots with hours-to-pitch) — densify −3h cannot grade live nowcast wiring  
2. Batter–pitcher matchup from pitch-level (not SP quality mul)  
3. Park-relative weather **totals-only** track  
4. Accept research-grade until a signal clears +0.010
