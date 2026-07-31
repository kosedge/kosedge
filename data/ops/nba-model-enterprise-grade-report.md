# NBA Model — Enterprise Grade Report

**Generated:** 2026-07-31  
**Phase reached:** Phase 0 complete · Phase 1 ingest scaffolded · Phase 2 calibration helpers stubbed  
**Model version:** `nba-v1-poss-sim`  
**Worker canary:** `nba-poss-sim-20260731-phase0b`

## Executive status

Possession-level Monte Carlo scaffold is live on model-service (`/nba/health`, `/nba/fair-lines`, `/nba/simulations/demo`). Pro desk `/pro/nba/fair-lines` reads the real API. Offseason empty slate is labeled honestly — no invented fair prices.

Walkforward metrics against closing lines are **awaiting outcomes** (July offseason; rolling box ingest not yet populated with a graded sample).

## Architecture

| Layer | Implementation |
|-------|----------------|
| Simulator | Possession MC with typed PBP event interfaces |
| Markets | ML / spread / total distributions + fair lines |
| Market blend | Thin-sample boost toward existing `odds_snapshots` (no Odds API historical burn) |
| Ingest | stats.nba.com scoreboard / box / PBP; SportsDataIO optional if key present |
| Persistence | `nba_market_projections`, `nba_game_context`, `nba_team_rolling_features`, `nba_possessions`, `nba_games_ingest` |

## Metrics (current)

| Metric | Value | Notes |
|--------|-------|-------|
| Graded games (spread) | 0 | Awaiting season / outcomes |
| Graded games (total) | 0 | Awaiting season / outcomes |
| Model spread MAE | — | Phase 2 |
| Close spread MAE | — | Baseline from `odds_snapshots` |
| Model total MAE | — | Phase 2 |
| ATS cover rate | — | Phase 2 |
| Determinism tests | Pass | Seed-stable unit tests |

## Publish policy

- **Mainlines:** research_only until walkforward sample exists.
- **Props:** queued until mainlines are honest (Phase 3). No cosmetic nudges.

## Next calibration steps

1. Nightly ingest → rolling features → context → sim (beat jobs registered).
2. Join projections to finals + closing spread/total from owned `odds_snapshots`.
3. Fit possession rates / pace; publish blend weights from walkforward (NFL lesson).
4. Refresh this report with MAE / bias / cover tables.

## Verify commands

```bash
curl -sS "$MODEL_SERVICE_URL/nba/health"
curl -sS "$MODEL_SERVICE_URL/nba/fair-lines"
```
