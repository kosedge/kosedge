# NFL team ID — collapse LA → LAR (single identity) — 2026-08-12

Date: 2026-08-12  
Branch: `feat/nfl-team-id-lar-canonical` → `deploy-vercel`  
Priority: P0 — Survivor/paths showed `LA 75.3% @ LV`; burns and SOS broke when `LA ≠ LAR`.

## Doctrine

One franchise = one `team_id`. Rams = **LAR** only. Chargers stay **LAC**. Never merge LAC into LAR.

## Before / after

| Surface | Before | After |
|---------|--------|--------|
| Survivor week slate `team` / `opponent` / `matchup_label` | `LA` (nflverse storage direction) | **LAR** |
| Used / available / locked picks | `LA` and `LAR` were two identities | Burning either removes Rams; emit **LAR** |
| Web chips / dropdowns (`NFL_SEASON_ENGINE_TEAMS`) | `"LA"` | `"LAR"` |
| `normalizeNflTeamCode("lar")` | `"LA"` | `"LAR"` |
| Wall-chart matchups (already keyed `LAR`) | Forced to `LA` on ingest | Stay **LAR** (SF @ LAR W1) |
| LAC | Chargers | Unchanged |
| nflverse SQL / `game_query` / depth packs | `LA` storage | **Unchanged** (lookup alias only) |

## Incorporate, don’t paint

- Engine survivor keys the path pool, schedule index, and used-set by canonical id (`LA`/`STL` → `LAR`).
- Lookups still accept storage aliases so SOS / win maps keyed `LA` still resolve.
- Web ingest canonicalizes survivor / plan / suggest-paths payloads so a stale engine cannot reintroduce `LA` on the desk.
- `LA` + `LAR` in the same planner slate is one franchise (duplicate-pick reject).

## Files touched

- `services/model-service/src/services/nfl_season_engine/survivor.py`
- `services/model-service/tests/test_nfl_season_engine_survivor.py`
- `apps/web/lib/nfl-season-engine-format.ts`
- `apps/web/lib/nfl-season-engine.ts`
- `apps/web/__tests__/lib/nfl-season-engine-format.test.ts`
- `apps/web/components/pro/nfl/SeasonEngineSurvivorClient.tsx`
- `apps/web/components/pro/nfl/SeasonEngineSurvivorPlannerClient.tsx`

## Intentionally not flipped (storage / other sports)

- `loaders.normalize_team_abbr` / `injury_paths.normalize_team_code` / `projected_sos.normalize_team` still map LAR→LA for nflverse keys
- `game_query.py` LAR→LA lookup
- WNBA Sparks `LA` in `team-research/directories-pro.ts`
- CFB

## Tests

- Engine: no raw `LA` in demo or packaged week-1 survivor JSON; `already_used=["LA"]` burns LAR; LA+LAR cannot double-pick; LAC still present
- Web: `normalizeNflTeamCode("LA"|"lar") === "LAR"`; wall-chart SF @ LAR; `rawLaRamsHits` fails dirty payloads

## Smoke

Survivor pick card + used list show **LAR** only (e.g. LAR vs SF / @ LV). Used chip LAR lights when engine returns a burned Rams alias.
