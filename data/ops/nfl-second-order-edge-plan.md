# NFL Second-Order Edge — Narrow Plan (updated)

**Branch:** `nfl-second-order-edge`  
**Constraint:** Extend `nfl_simulator` / `nfl_handicapping_framework` / player engine; preserve `nfl-v1.5-matchup-sim`, leakage lags, champion/challenger.

## Modules (narrow ship / defer)

| ID | Module | Status |
|----|--------|--------|
| **E** | Injury/practice info velocity | **SHIPPED** (priority) |
| **H** | Enhanced weather (VC) + travel×weather | **SHIPPED** (graceful skip) |
| **B** | Personnel efficiency + light sub elasticity | **SHIPPED** (kept; elasticity weight light) |
| **A** | Thin 4th-down / tempo rates | **SHIPPED** (slimmed; not complex latent) |
| **D** | Error-regime uncertainty widening | **SHIPPED** (no point shift) |
| C | Org belief / OTC / Spotrac | **DEFERRED** |
| F | Same-game correlation / SGP | **DEFERRED** |
| G | Scheme-fit interactions | **DEFERRED** |
| PFF | Scrape / grades skeleton | **STRIPPED / DEFERRED** |

See `data/ops/nfl-narrow-second-order-report.md` for full ops report.

## Migrations
- `043_nfl_second_order_edge.sql` — foundation
- `044_nfl_narrow_second_order.sql` — info-velocity index/cache + matchup cols

## Env vars (active)
| Var | Purpose |
|-----|---------|
| `VISUAL_CROSSING_API_KEY` | Weather (optional; graceful skip) |
| `NFL_VC_WEATHER_ENABLED` | Prefer VC when keyed |
| `NFL_FRAMEWORK_*_ENABLED` | Kill-switches for personnel / coach / info_velocity / travel_weather / error_regime |

## Risks
1. Coverage — disabled factors do not penalize; missing data still does.
2. PBP re-normalize required for personnel/coach materializers.
3. Leakage — weekly features join `as_of_week = game.week - 1`.
4. Promote only if holdout ablation does not worsen (ST KAV / QB discipline).

## Dry-run
See narrow report §5.
