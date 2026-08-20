# Safe NFL rematerialize entrypoint (post week-22 wipe class)

**LIVE stays false.** Do not enqueue bare `season=` rebuilds.

## Never do this

```text
POST /nfl/ops/rebuild-props-layers?season=2025
POST /api/jobs/run-nfl-props-layer-rebuild?season=2025
POST /nfl/ops/materialize-player-baselines?season=2025
```

On workers **before this patch is deployed**, omitted `week`/`weeks` resolved to
`MAX(week)` on `nfl_dp_player_usage_weekly` (week **22** for 2023–25) and the
task landed on Celery `default`. That is the poison class from #268 / LIVE
smoke 2026-08-20. Until the worker image includes this patch, **always pass
explicit `weeks=1,2,…,18`**. After deploy, omitted weeks expand to 1–18.

Beat must **not** schedule `run_nfl_props_layer_rebuild` or
`materialize_nfl_player_baseline_projections`. Cycle week is clamped to 1–18.

## Do this

Full regular-season features + baselines + box + props (weeks default **1–18**):

```text
POST /nfl/ops/rebuild-props-layers?season=2026
# equivalent explicit:
POST /nfl/ops/rebuild-props-layers?season=2026&weeks=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18
```

Jobs route to the `models` queue. Then SUM spine draft ranks:

```text
POST /nfl/ops/materialize-fantasy-draft-rankings?season=2026
```

Single-week baselines/features/fantasy **require** `week=`.

Playoff week 22 is allowed only when passed explicitly (`week=22` or `weeks=22`).

## Drain leftover poison (before any worker bounce)

```text
GET  /nfl/ops/celery-queues
POST /nfl/ops/celery-drain-poison-remats?confirm=true&trim_mlb_nowcast=true
```

Then bounce **worker only**. Prove a controlled remat completes with `weeks` 1–18.
