# NBA Model Build Plan

**Status:** Phase 0 scaffold shipped · Phase 1 ingest started  
**Canary / worker_build_id:** `nba-poss-sim-20260731-phase0`  
**Default model version:** `nba-v1-poss-sim`  
**Prod web branch:** `deploy-vercel`  
**Model service:** Railway (`scripts/deploy-railway-model-service.sh`)

## Architecture (locked)

- Mirror NFL matchup sim + MLB pitch-by-pitch philosophy.
- **v1 = possession-level Monte Carlo** → ML / spread / total distributions.
- Typed **event-PBP interfaces** (`PossessionEvent`, `PossessionEventType`, shot/foul/rebound/FT) under the hood so chains deepen without rewrite.
- No college props. Do **not** burn Odds API credits on historical re-pull (~3M reserved for live). Market blend reads existing `odds_snapshots` only.

## Phase 0 — Scaffold (DONE)

| Deliverable | Location |
|-------------|----------|
| `NbaGameInputs` + possession MC | `services/model-service/src/services/nba_possession_simulator.py` |
| Schema ensure | `services/model-service/src/services/nba_schema.py` |
| Routes: health, fair-lines, demo/sim, ops | `services/model-service/src/routes/nba.py` |
| Celery `run_nba_market_simulations` + canary | `services/model-service/src/tasks.py` |
| Router registration | `main.py`, `routes/__init__.py`, `celery_app.py`, beat schedule |
| Pro desk wired to real API | `/pro/nba/fair-lines`, `lib/nba-fair-lines.ts`, `resolve-kei-lines.ts` |
| Tests | `tests/test_nba_possession_simulator.py`, `tests/test_nba_routes.py` |

Fair-lines empty slate is labeled honestly (`slate_status: offseason_empty | no_projections_yet`).

## Phase 1 — Ingest + features (IN PROGRESS)

| Deliverable | Location / notes |
|-------------|------------------|
| stats.nba.com scoreboard / box / PBP | `services/model-service/src/services/nba_data.py` |
| Schedule ingest task | `pull_nba_schedule_ingest` → `nba_games_ingest` |
| PBP → possessions | `derive_possessions_from_pbp` → `nba_possessions` |
| Rolling pace / ORtg / DRtg / 3PT | `materialize_nba_team_rolling_features` → `nba_team_rolling_features` |
| Context assemble | `pull_nba_context_snapshot` → `nba_game_context` |
| SportsDataIO | Optional only if keys already present |

Availability/rest from public endpoints: rest_days columns exist on context; empirical rest tables next.

## Phase 2 — Calibrate

1. Fit possession rates + pace; walkforward vs closing spread/total from existing `odds_snapshots`.
2. Market blend + thin-sample rules (NFL lessons already stubbed in simulator).
3. Publish policy; nightly assemble → sim → persist (beat jobs registered).
4. Metrics → `data/ops/nba-model-enterprise-grade-report.md`.

## Phase 3 — Props (ONLY after mainlines honest)

- Reuse existing NBA prop snapshots; role/minutes integrity; no cosmetic nudges.
- Stub/queue until Phase 2 incomplete — do not rush fake props.

## Verify

```bash
# Model service
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/fair-lines
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/nba/simulations/demo?simulations=800&seed=42'

# Local unit tests
cd services/model-service && python -m pytest tests/test_nba_possession_simulator.py tests/test_nba_routes.py -q
```

## Constraints

- Research-first UI copy.
- Preserve DeploymentRecovery / BootShell / SportProShell.
- Restore `data_platform_nfl` if vendor sync dirties.
