# NBA Model — Enterprise Grade Report

**Generated:** 2026-07-31 (Phase 2)  
**Phase reached:** Phase 2 — close-line join fix + calibrate + publish posture  
**Model version:** `nba-v1-poss-sim`  
**Worker canary:** `nba-poss-sim-20260731-phase2`  
**SHA:** *(filled after deploy)*  
**Railway CI:** *(filled after deploy)*  
**Vercel Production:** *(filled after deploy)*

## Executive status

Phase 2 fixes the close-line soft-miss that blocked real calibration in Phase 1
(`n_with_close_lines=0`). Densified odds are reused (no large Odds API burn).
Publish posture remains **research_only** for mainlines until close-line ATS
clears evidence floors. Props not published. NFL/MLB preserved.

## Close-line join fix (root cause)

| Failure mode | Cause | Fix |
|--------------|-------|-----|
| Abbr mismatch | Densify wrote Odds full names + heuristic abbrs (`BOCE`) while ingest uses canonical keys (`BOS`) | Join on **full name OR abbr aliases**; `repair_nba_odds_team_abbrs` rewrites `teams.abbr` |
| Date TZ skew | UTC `commence_time` can shift `games.game_date` vs ingest `gdte` (ET) | Match ET tip date **or** `game_date ± 1 day`; new densify stores ET calendar date |
| season_year | Calendar year split mid-season | NBA season start year (Aug–Jul) in `_ensure_hierarchy` |
| sport key | Already `basketball_nba` → `leagues.code='nba'` | Unchanged; inventory still joins via `l.code='nba'` |

## Live Postgres inventory (truth)

Read from model-service only (`/nba/ops/inventory`). joyful-clarity cloud token
Postgres is **not** the warehouse.

| Metric | Phase 1 after densify | Phase 2 (pre-calibrate) |
|--------|----------------------|-------------------------|
| `odds.mainline_games` | **1345** | owned (no re-densify) |
| `odds.odds_snapshot_rows` | **32698** | owned |
| `nba_games_ingest` | **5583** | **5583** |
| `nba_team_game_features` | **3794+** | enriching |
| `nba_market_projections` | 0 (offseason) | 0 unless slate exists |

## Odds API spend

| Item | Value |
|------|-------|
| Phase 1 densify | ~15k credits (retained) |
| Phase 2 densify | **skipped** (`densify_odds=false`) |
| Floor policy | ≥1.5M remaining |

## Metrics (walkforward)

| Metric | Phase 1 | Phase 2 |
|--------|---------|---------|
| Graded games | 60 | *(live)* |
| `n_with_close_lines` | **0** | **target >> 0** *(live)* |
| Model spread MAE | 14.26 | *(live)* |
| Model total MAE | 17.28 | *(live)* |
| Close spread MAE | — | *(live)* |
| Close total MAE | — | *(live)* |
| Model ATS (vs actual) | 51.7% | *(live)* |
| Model vs close ATS | — | *(live)* |
| Blend hint | n/a | *(live)* |
| Market blend weights | 0.25 / 0.25 | **0.40 / 0.45** (+ thin-sample boost) |

## Letter grades

| Gate | Grade | Notes |
|------|-------|-------|
| Data ownership / densify discipline | **A** | Owned mainlines; no Phase-2 burn |
| Close-line join | **B+** pending live `n_with_close` | Code+tests green; prove on Railway |
| Mainline calibration | **C+** → retune | Phase-1 MAE weak without closes; blend raised on evidence |
| Publish honesty | **A** | research_only; props queued; offseason empty |
| Nightly/beat pipeline | **B+** | `run_nba_daily_cycle` + 3am beat |
| Overall Phase 2 | **B** pending live walkforward fill | |

## Architecture

| Layer | Implementation |
|-------|----------------|
| Simulator | Possession MC + typed PBP events |
| Ingest | data.nba.com schedule + gamedetail |
| Features | `nba-rolling-gamelog-v1` |
| Close lines | Owned `odds_snapshots` via name/abbr/ET join |
| Publish | `nba_publish_policy` — PASS default |
| Nightly | context → sim → persist when slate exists |

## Phase 2 exit criteria

| Criterion | Met? |
|-----------|------|
| Close-line join `n_with_close_lines >> 0` | pending live |
| Walkforward with real closes + blend tune | pending live |
| Publish policy research_only / props queued | **Y** |
| Nightly/beat daily cycle | **Y** |
| Enterprise report + letter grades | **Y** (live metrics TBD) |
| Canary phase2 + Railway + deploy-vercel | pending |

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/repair-nba-odds-team-abbrs'
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-phase2-calibrate?walkforward_games=80&simulations=1000'
```
