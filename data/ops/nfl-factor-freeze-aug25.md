# NFL Factor Freeze — August 25, 2026

**Freeze date:** 2026-08-25  
**Branch:** `nfl-second-order-edge`  
**Policy:** `spread_play_v2_cap7`  
**Product gate default:** YELLOW

## Locked ON

| Factor | Notes |
| --- | --- |
| KAV v3 | Core margin/total engine |
| H `travel_weather_interaction` | Ablation ATS +0.71pp confirmatory |
| D `error_regime` | Uncertainty widen / confidence penalty only |

## Locked OFF (do not re-enable without holdout)

| Factor | Why |
| --- | --- |
| E `info_velocity` | Confirmatory ATS 0.729 → 0.694 (−3.5pp) |
| B `personnel_efficiency` | No `offense_personnel` in public PBP |
| A `coach_aggression` | Slight ATS/CLV regress |

## Also frozen

- PLAY band `[2.5, 7.0)` — do not widen; do not chase full-slate 60%.
- Market blend weights — no light blend recal unless unused holdout clears.
- Props `PLAY_STAKE_ELIGIBLE=false`.
- Totals sides-only (`TOTAL_PLAY_ENABLED=false`).
- Preseason info desk — never mix PRE ATS into season PLAY gates.

## Operator checklist

See `data/ops/nfl-factor-freeze-operator-checklist.md` (env table + day-of checks).

## Unfreeze protocol

1. Pre-register candidate + holdout seasons.
2. Run confirmatory PLAY holdout + ablation.
3. Update `docs/NFL_ENTERPRISE_GATES.md` + this file with decision.
4. Only then flip env/code defaults.
