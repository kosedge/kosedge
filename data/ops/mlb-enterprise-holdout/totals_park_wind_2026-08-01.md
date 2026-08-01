# MLB totals-only park-relative wind densify (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `7463805c-da6c-446a-84ee-e80dc7016e26` (`run_mlb_totals_park_wind_ablation` W0/W1)  
**PR:** [#59](https://github.com/kosedge/kosedge/pull/59)  
**Stack held:** S0 ML path (absolute wind-dir mul ON for run rates); park-rel applied **post-sim to totals only**  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Artifact:** `totals_park_wind_2026-08-01.json`

## What was built

1. `PARK_CF_BEARING_DEG` map + wind-from → wind-to conversion
2. Flag `MLB_TOTALS_PARK_REL_WIND_ENABLED` (default **off**)
3. Post-sim totals mul only — **fg/f5 win probs and spreads unchanged by construction**
4. Domes/retractable suppressed; reliability dampening respected
5. ML absolute wind-dir path left alone (S2 taught not to kill RL via wind-dir-off)

## Intersection-n (n = 476)

| Config | ML CLV | RL CLV | Total CLV | WF Brier | MAE | Leak |
|--------|-------:|-------:|----------:|---------:|----:|-----:|
| W0 off | +0.00386 | +0.025 | +0.002 | **0.24964** | **3.480** | **0** |
| W1 on | **+0.00391** | +0.025 | **+0.004** | 0.25039 | 3.487 | **0** |

W1 − W0: ML **+0.00005**, total CLV **+0.0021**, MAE **+0.007** (worse), Brier worse.

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** |
| ML not regress | flat/up | **PASS** (tiny +0.00005) |
| Totals improve | MAE **or** total CLV | **MIXED** — total CLV +0.002; **MAE worse** |
| Meaningful lift | clear, not noise | **FAIL** |

Auto-task `ship_totals_park_rel_wind=true` used OR logic on CLV/MAE. **Human override: NO-SHIP** — MAE regresses, CLV delta is noise-scale, Brier softens.

## Decision

**Do not flip `MLB_TOTALS_PARK_REL_WIND_ENABLED`.** Keep wiring (CF bearings + totals-only path) for a sharper park/weather model later. Production S0 unchanged; ML wind-dir stays ON.
