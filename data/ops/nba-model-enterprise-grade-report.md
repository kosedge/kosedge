# NBA Model — Enterprise Grade Report

**Generated:** 2026-07-31 (Phase 1 pass)  
**Phase reached:** Phase 1 (ingest/features/densify path) — awaiting Railway bootstrap results  
**Model version:** `nba-v1-poss-sim`  
**Worker canary:** `nba-poss-sim-20260731-phase1`

## Executive status

Possession Monte Carlo remains live. Phase 1 adds foundation SQL, leaguegamelog season ingest, rolling team features (pace/ORtg/DRtg/3PT/rest), player minutes/usage stubs, inventory endpoints, and a **credit-capped** NBA mainline densify path (only if empty).

No fake KEI. Props not published.

## Live Postgres inventory (truth)

### joyful-clarity Railway Postgres (cloud-agent token)

| Check | Value |
|-------|-------|
| Host | `sakura.proxy.rlwy.net` (public) / `postgres.railway.internal` |
| `information_schema` public tables | **0** |
| Verdict | **Not the model warehouse.** Do not use for NBA/NFL/MLB counts. |

### brave-art model-service DB (authoritative)

Read after phase1 deploy:

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
```

| Metric | Before Phase 1 bootstrap | After |
|--------|--------------------------|-------|
| `odds.mainline_games` (l.code=nba) | _pending inventory endpoint_ | _pending_ |
| `odds.odds_snapshot_rows` | _pending_ | _pending_ |
| `games.hierarchy_nba` | _pending_ | _pending_ |
| `nba_games_ingest` | _pending_ | _pending_ |
| `nba_team_game_features` | _pending_ | _pending_ |
| `nba_team_rolling_features` | _pending_ | _pending_ |

Explore summaries that reported `mainline_games=0` for NBA must be re-verified against `/nba/ops/inventory` on model-service — not joyful-clarity.

## Odds API credits

| Item | Value |
|------|-------|
| Probe (historical NBA one-shot, 2026-07-31) | ~30 credits (`x-requests-last`) |
| Remaining after probe | **2,989,372** |
| Used | ~2,010,628 |
| Densify policy | Cap **≤300k** this pass; floor **≥1.5M** remaining; skip if `mainline_games ≥ 100` |
| Markets | h2h, spreads, totals only (open+close on game-days) |

## Architecture

| Layer | Implementation |
|-------|----------------|
| Simulator | Possession MC + typed PBP events |
| Ingest | `stats.nba.com/leaguegamelog` seasons 2021–22…2024–25 |
| Features | `nba_team_game_features` → rolling pack `nba-rolling-gamelog-v1` |
| Rest | Derived from prior `nba_games_ingest` dates |
| Player stubs | `nba_player_game_stubs` (minutes/usage proxy) — not published |
| Odds | Owned snapshots first; targeted densify if empty |
| Persistence | See `infra/db/045_nba_model_foundation.sql` |

## Metrics (current)

| Metric | Value | Notes |
|--------|-------|-------|
| Graded games (spread) | pending bootstrap | Phase 1 walkforward sample |
| Graded games (total) | pending bootstrap | |
| Model spread MAE | — | fill after `run_nba_walkforward_sample` |
| Close spread MAE | — | requires densify or owned closes |
| ATS cover rate | — | |
| Determinism tests | Pass (unit) | |

## Publish policy

- **Mainlines:** research_only until walkforward sample lands.
- **Props:** queued (Phase 3).

## Phase 1 exit criteria

| Criterion | Met? |
|-----------|------|
| Foundation tables present (`045` / ensure) | Y (code) / pending Railway apply |
| Season ingest 2021–2025 rows | pending bootstrap |
| Rolling features wired into context/sim | Y (code) |
| Inventory truth documented | partial (joyful-clarity empty verified; brave-art pending endpoint) |
| Odds densify only if empty + spend documented | Y (code path) |
| Thin walkforward or blockers documented | pending bootstrap |
| Canary phase1 + Railway + deploy-vercel | pending deploy |

## Verify

```bash
curl -sS "$MODEL_SERVICE_URL/nba/health"
curl -sS "$MODEL_SERVICE_URL/nba/ops/inventory"
curl -sS -X POST "$MODEL_SERVICE_URL/api/jobs/run-nba-phase1-bootstrap?max_credit_spend=300000"
```
