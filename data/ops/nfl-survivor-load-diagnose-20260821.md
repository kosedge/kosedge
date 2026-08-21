# NFL survivor load — diagnose (2026-08-21)

**Surface:** `/pro/nfl/survivor?mode=planner` vs Fantasy / Overview.

Measured 2026-08-21 against Railway `model-service-production-e253` (warm worker) and www.

## What was slow

Not the whole site. Isolated to Survivor **default load**.

| Call | Time (warm) | Size | On page load? |
|------|-------------|------|----------------|
| `GET /nfl/season-engine/status` | 0.45s | 21 KB | **Yes — blocked RSC** |
| `loadSeasonEngineMatchups` (fair-lines, 14d) | board budget up to 12s | — | **Yes — only used for `defaultWeek`** |
| `POST /survivor/plan` n=**2000**, empty picks, top_n=32 | 0.29s **cache hit** / ~0.8s+ n=50 miss | **475 KB** | **Yes, after hydrate + 450ms** |
| `POST /survivor/suggest-paths` n=2000 | 0.27s warm | 25 KB | **Yes, parallel with plan** |
| www HTML TTFB | 0.38s | 47 KB | then client waits on plan |

Cold 2000-sim pool build is the hang users feel: interactive Game Boxes docs already cite ~65s@2k. Planner sent **n=2000 twice** (plan + suggest) and showed “Running season paths for the full slate…” until the 475 KB plan arrived. Weeks did not paint.

n=50 empty plan: **0.76s miss / 0.36s warm**, 460 KB (diagnostics + 18×32 rows). Slim no-diag top_8: 139 KB.

## Client blocking

`SeasonEngineSurvivorPlannerClient` on hydrate:

1. `POST /api/.../plan` with `NFL_DEFAULT_N_SURVIVOR_PATHS = 2000`
2. `POST /api/.../suggest-paths` with the same n
3. Placeholder copy: “Waiting for planner rankings…” / full-page spinner

Page `force-dynamic` awaited status **and** fair-lines before the shell.

## What is already fine

- Path math / scoring knobs
- Railway path-pool cache (warm plan ~300ms)
- Helper mode waits for an explicit Rank click
- Fantasy / Edge Board unused by this path

## Fix direction

Light first paint (18-week shell, no fair-lines). Interactive n=50. Cache empty plan. Suggest-paths on demand. Honest timeout if the engine is cold.
