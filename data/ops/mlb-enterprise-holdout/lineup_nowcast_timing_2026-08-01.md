# MLB lineup / nowcast timing densify (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `080fbeff-22dd-4a7f-bcd4-6c4e8d00bba4` (`run_mlb_lineup_timing_ablation` L0/L1)  
**PR:** [#58](https://github.com/kosedge/kosedge/pull/58)  
**Stack held:** S0 (HFA 1.025, matchup ON, wind-dir ON, era_whip, bullpen role off)  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Artifact:** `lineup_nowcast_timing_2026-08-01.json`

## What was built

### Always-on wiring (correctness; not a CLV ship claim)
1. Clear `fetch_game_lineup_features` LRU before context/nowcast pulls  
2. Live nowcast freshness = ~1.0 on successful feed (stop damping with stale `updated_at`)  
3. Pass `bullpen_quality_*` into nowcast sim inputs  
4. Schedule hydrate includes `lineups`  
5. Skip pitcher batting slots in lineup strength (DH path)  
6. Ops: emit `sp_change_games` on nowcast summary  

### Flagged timing sharpness (`MLB_LINEUP_TIMING_MODE`)
| Mode | Behavior |
|------|----------|
| **off** (default / L0) | Production confidence path |
| **sharp** (L1) | Per-side confirm, both-sides gate for `lineup_confirmed`, firmness bump, late SP clear ≤3h when cards real; densify applies at −3h stamp |

## Intersection-n (n = 476)

| Config | ML CLV | RL CLV | Total CLV | WF Brier | MAE | Leak |
|--------|-------:|-------:|----------:|---------:|----:|-----:|
| L0 timing off | **+0.00413** | +0.013 | +0.002 | **0.24955** | 3.485 | **0** |
| L1 timing sharp | +0.00389 | +0.013 | +0.002 | 0.25042 | **3.478** | **0** |

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** |
| Intersection ML CLV | ≥ +0.010 | **FAIL** (best L0 +0.00413) |
| L1 beats L0 on ML | clear lift | **FAIL** (L1 −0.00024) |
| Densify base Brier | ≤ 0.248 | **FAIL** |

## Decision

**Do not flip `MLB_LINEUP_TIMING_MODE=sharp`.** Production stays timing **off**.

**Do keep always-on wiring fixes** — they correct live nowcast staleness / SP-clear / BP quality bugs. Densify at −3h cannot fully grade live late-info CLV; L1’s densify effect is a mild confidence/firmness rewrite that **softened** ML CLV.

### Why densify understates nowcast value
Historical resim stamps projections at `start_time − 3h` using context cards, not a true hours-to-pitch nowcast ladder. Wiring wins show up in live pre-lock repricing; intersection densify only sees the sharp confidence/firmness mul — which failed the gate.

## Next levers (honest)

1. Persist `(game_id, observed_at, hours_to_pitch, lineup_hash, sp_*)` snapshots and grade late-info CLV slice  
2. Batter–pitcher pitch-level matchup (not another SP quality / confidence mul)  
3. Park-relative weather totals-only  
4. Research-grade hold until +0.010 intersection ML clears
