# NBA Model Build Plan

**Status:** Phase 3 — player props research board live  
**Canary / worker_build_id:** `nba-poss-sim-20260731-phase3-props`  
**Default model version:** `nba-v1-poss-sim`  
**Props model version:** `nba-player-props-v1`  
**Prod web branch:** `deploy-vercel`  
**Model service:** Railway brave-art

## Architecture (locked)

- Mirror NFL matchup sim + MLB pitch-by-pitch philosophy.
- **v1 = possession-level Monte Carlo** → ML / spread / total distributions.
- Typed **event-PBP interfaces** under the hood.
- Props: pts/reb/ast/threes from minutes×usage stubs + team pace/ORtg; research-only tags.
- Odds: owned densify; no large re-burn.

## Phase 0 — Scaffold (DONE)

Canary `nba-poss-sim-20260731-phase0b`.

## Phase 1 — Ingest + features (DONE)

| Deliverable | Notes |
|-------------|-------|
| data.nba.com ingest | 5583 games; features + rolling |
| Targeted densify | 1345 mainline games / 32,698 rows (~15k credits) |
| Canary | `nba-poss-sim-20260731-phase1` |

## Phase 2 — Calibrate (DONE)

| Deliverable | Notes |
|-------------|-------|
| Close-line join | 79/80 with real closes |
| Walkforward | spread MAE 12.64 / total 14.98 / ATS 57.5% |
| Publish | research_only mainlines |
| Canary | `nba-poss-sim-20260731-phase2` |

## Phase 3 — Props (DONE)

| Deliverable | Location |
|-------------|----------|
| Projection | `nba_player_prop_projection.py` |
| Edge policy | `nba_prop_edge_policy.py` (role-collapse Under refuse; stake_eligible=False) |
| Edges table | `nba_player_prop_model_edges` + `infra/db/046_nba_player_props.sql` |
| Materialize | `materialize_nba_player_props_edges` |
| API | `GET /nba/props/board` |
| Jobs | `/api/jobs/run-nba-phase3-props-bootstrap` |
| Web | `/pro/nba/props` via `nba-props-board.ts` |
| Canary | `nba-poss-sim-20260731-phase3-props` |

### Bootstrap

```bash
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-phase3-props-bootstrap?lookback_games=8&limit_players=200'
curl -sS 'https://model-service-production-e253.up.railway.app/nba/props/board'
```

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/fair-lines
curl -sS https://model-service-production-e253.up.railway.app/nba/props/board
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
cd services/model-service && python -m pytest tests/test_nba_*.py -q
```

## Constraints

- Research-first. Preserve NFL/MLB.
- No college props.
- No stake-eligible PLAY until props holdout clears.
