# NBA Model — Enterprise Grade Report

**Generated:** 2026-07-31 (Phase 1)  
**Phase reached:** Phase 1 complete (ingest + features + densify + thin walkforward)  
**Model version:** `nba-v1-poss-sim`  
**Worker canary:** `nba-poss-sim-20260731-phase1`  
**SHA:** `de702d0`  
**Railway CI:** [30670636129](https://github.com/kosedge/kosedge/actions/runs/30670636129) success  
**Vercel Production:** `kosedge-j4tm6hw5v` (Ready)

## Executive status

Phase 1 landed on Railway. Live inventory confirms NBA mainlines were **empty before densify** and are now populated. Schedule/box features ingest via **data.nba.com** (stats.nba.com times out from Railway egress). No fake KEI. Props not published.

## Live Postgres inventory (truth)

### joyful-clarity Railway Postgres (cloud-agent token)

| Check | Value |
|-------|-------|
| Public tables | **0** |
| Verdict | Not the model warehouse |

### brave-art model-service DB (authoritative via `/nba/ops/inventory`)

| Metric | Before densify | After densify |
|--------|----------------|---------------|
| `odds.mainline_games` | **0** | **1345** |
| `odds.odds_snapshot_rows` | **0** | **32698** |
| `games.hierarchy_nba` | 0 | **1347** |
| `nba_games_ingest` | **5583** | **5583** |
| `nba_team_game_features` | ~1650→ | **3444+** (details still enriching) |
| `nba_team_rolling_features` | 0 | **34** |
| `nba_player_game_stubs` | **1557** | **1557** |
| `nba_market_projections` | 0 | 0 (offseason) |

**Explore note verified:** enterprise pull summary `mainline_games=0` for NBA was **true** on the live model-service DB before this densify.

## Odds API spend (documented)

| Item | Value |
|------|-------|
| Credits before densify | 2,989,372 |
| Credits after densify | 2,974,372 |
| **Spent this densify** | **~15,000** |
| Probe earlier (1 historical call) | ~30 |
| Cap / floor policy | cap 300k / floor ≥1.5M |
| Markets | h2h, spreads, totals |
| Bookmakers | DraftKings, FanDuel |
| Window | 2023-10-24 → 2025-06-22 game-days |
| Requests | 500 (open+close style snapshots) |
| Result | `mainline_games` 0 → 1345 |

## Ingest row counts

| Source | Count |
|--------|-------|
| Seasons | 2021-22 … 2024-25 |
| `nba_games_ingest` | 5583 |
| Team game features (gamedetail) | 3444+ (still filling) |
| Player stubs | 1557 |
| Rolling features (30 teams) | 34 rows |

## Architecture

| Layer | Implementation |
|-------|----------------|
| Simulator | Possession MC + typed PBP events |
| Ingest | **data.nba.com** schedule + gamedetail (primary); stats.nba.com fallback |
| Features | `nba-rolling-gamelog-v1` pace/ORtg/DRtg/3PT/rest |
| Odds | Targeted densify when empty; skip if owned |
| Foundation SQL | `infra/db/045_nba_model_foundation.sql` |

## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Graded games (spread/total) | **60** | thin walkforward sample |
| Model spread MAE | **14.26** | vs actual margin (pre-calibration) |
| Model spread bias | -2.41 | home perspective |
| Model total MAE | **17.28** | |
| Model total bias | -5.97 | |
| ATS cover rate | **51.7%** | |
| Close spread/total MAE | — | `n_with_close_lines=0` in sample (abbr join soft-miss; Phase 2) |
| Determinism tests | Pass | 19 unit tests |
| Publish policy | research_only mainlines; props queued | |

## Phase 1 exit criteria

| Criterion | Met? |
|-----------|------|
| Foundation tables present | **Y** |
| Season ingest 2021–2025 rows | **Y** (5583) |
| Rolling features wired into context/sim | **Y** (code + 34 rolling rows) |
| Inventory truth documented | **Y** |
| Odds densify only if empty + spend documented | **Y** (~15k credits) |
| Thin walkforward or blockers documented | **Y** (n=60; close-line join soft-miss noted) |
| Canary phase1 + Railway + deploy-vercel | **Y** |

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-walkforward-sample?limit_games=60'
```
