# NFL Second-Order Edge — Narrow Plan (updated)

**Branch:** `nfl-second-order-edge`  
**Constraint:** Extend `nfl_simulator` / `nfl_handicapping_framework` / player engine; preserve `nfl-v1.5-matchup-sim`, leakage lags, champion/challenger.

## Modules (narrow ship / defer)

| ID | Module | Status |
|----|--------|--------|
| **H** | Travel×weather (Open-Meteo primary; VC optional overlay) | **PROMOTED** (defaults ON) |
| **D** | Error-regime uncertainty widening | **PROMOTED** (no point shift) |
| **E** | Injury/practice info velocity | **KILLED** (holdout ATS −3.5pp) |
| **B** | Personnel efficiency + light sub elasticity | **KILLED** (no public personnel path) |
| **A** | Thin 4th-down / tempo rates | **KILLED** (holdout regress) |
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
| `VISUAL_CROSSING_API_KEY` | Optional weather upgrade for H (graceful skip if absent) |
| `NFL_VC_WEATHER_ENABLED` | Prefer VC when keyed (default true) |
| `NFL_FRAMEWORK_TRAVEL_WEATHER_ENABLED` | H kill-switch (default **true** / promoted) |
| `NFL_FRAMEWORK_ERROR_REGIME_ENABLED` | D kill-switch (default **true** / promoted) |
| `NFL_FRAMEWORK_{INFO_VELOCITY,PERSONNEL,COACH_AGGRESSION}_ENABLED` | Default **false** (killed) |

### Visual Crossing signup (user action)

1. Open https://www.visualcrossing.com/weather-api → **Get Your Free API Key**
2. Paste into local `.env` / `infra/.env.docker` as `VISUAL_CROSSING_API_KEY=...`
3. Set the same var on Railway **model-service** production (do not invent a key)
4. Free tier ~1000/day; code caches ~18h + 1.1s min interval — do not disable cache

## Risks
1. Coverage — disabled factors do not penalize; missing data still does.
2. PBP re-normalize required for personnel/coach materializers.
3. Leakage — weekly features join `as_of_week = game.week - 1`.
4. Promote only if holdout ablation does not worsen (ST KAV / QB discipline).

## Dry-run
See narrow report §5.
