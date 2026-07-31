# NBA Model Build Plan

**Status:** Phase 1 in progress (ingest + features + inventory + densify path)  
**Canary / worker_build_id:** `nba-poss-sim-20260731-phase1`  
**Default model version:** `nba-v1-poss-sim`  
**Prod web branch:** `deploy-vercel`  
**Model service:** Railway brave-art (`scripts/deploy-railway-model-service.sh` / GH Actions)

## Architecture (locked)

- Mirror NFL matchup sim + MLB pitch-by-pitch philosophy.
- **v1 = possession-level Monte Carlo** → ML / spread / total distributions.
- Typed **event-PBP interfaces** under the hood.
- No college props. No fake KEI. Props publish deferred to Phase 3.
- Odds: read owned `odds_snapshots` first; **targeted** historical densify only if NBA mainlines empty, hard credit cap (~200–400k), leave ≥1.5M for live.

## Phase 0 — Scaffold (DONE)

| Deliverable | Location |
|-------------|----------|
| `NbaGameInputs` + possession MC | `services/model-service/src/services/nba_possession_simulator.py` |
| Schema ensure | `services/model-service/src/services/nba_schema.py` |
| Routes / Celery / Pro desk | `/nba/*`, `tasks.py`, `/pro/nba/fair-lines` |
| Canary | `nba-poss-sim-20260731-phase0b` @ SHA `514ca97` |

## Phase 1 — Ingest + features (THIS PASS)

| Deliverable | Location / notes |
|-------------|------------------|
| Foundation SQL | `infra/db/045_nba_model_foundation.sql` (+ runtime `ensure_nba_model_tables`) |
| Season ingest (leaguegamelog) | `pull_nba_season_ingest` → `nba_games_ingest` + `nba_team_game_features` |
| Rolling pace/ORtg/DRtg/3PT/rest | `materialize_nba_team_rolling_features` → `nba_team_rolling_features` |
| Player minutes/usage stubs | `nba_player_game_stubs` (not published) |
| Context → sim ratings | `pull_nba_context_snapshot` uses rolling features + rest |
| Inventory truth | `GET /nba/ops/inventory`, `GET /api/jobs/nba-inventory` |
| Targeted odds densify | `pull_nba_historical_odds_densify` (skip if owned) |
| Thin walkforward | `run_nba_walkforward_sample` |
| Bootstrap orchestration | `run_nba_phase1_bootstrap` / `POST /api/jobs/run-nba-phase1-bootstrap` |

### DB inventory note (critical)

Cloud-agent `RAILWAY_TOKEN` is a **joyful-clarity** project token. That Postgres has **0 public tables** and is **not** the brave-art model-service warehouse. Live NBA odds/games counts must be read from model-service:

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
curl -sS https://model-service-production-e253.up.railway.app/api/jobs/nba-inventory
```

Document before/after counts from those endpoints into the enterprise grade report.

### Bootstrap

```bash
# After Railway deploy of phase1 canary:
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-phase1-bootstrap?max_credit_spend=300000&walkforward_games=60'
```

## Phase 2 — Calibrate

1. Fit possession rates + pace; walkforward vs closing spread/total.
2. Market blend + thin-sample rules.
3. Publish policy; nightly assemble → sim → persist.
4. Metrics → `data/ops/nba-model-enterprise-grade-report.md`.

## Phase 3 — Props (ONLY after mainlines honest)

- Reuse NBA prop snapshots; role/minutes integrity; no cosmetic nudges.

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/fair-lines
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
cd services/model-service && python -m pytest tests/test_nba_possession_simulator.py tests/test_nba_routes.py tests/test_nba_data.py -q
```

## Constraints

- Research-first UI copy. Preserve NFL/MLB.
- Preserve DeploymentRecovery / BootShell / SportProShell.
