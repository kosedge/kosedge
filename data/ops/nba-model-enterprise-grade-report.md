# NBA Model — Enterprise Grade Report

**Generated:** 2026-07-31 (Phase 3)  
**Phase reached:** Phase 3 complete (props research board)  
**Model version:** `nba-v1-poss-sim`  
**Props model:** `nba-player-props-v1`  
**Worker canary:** `nba-poss-sim-20260731-phase3-props`  

## Executive status

Phases 0–2 remain live (possession sim, densify, close-line join, research_only
mainlines). Phase 3 adds player props from stub minutes/usage + team pace/ORtg
for pts/reb/ast/threes. Tags are **research_only** (`stake_eligible=False`);
role-collapse Under refusal ports the NFL props lesson. Market lines join when
`player_prop_market_snapshots` exist — never invent books. Offseason fair-lines
stay empty/honest. NFL/MLB preserved.

## Close-line join fix (root cause)

| Failure mode | Cause | Fix |
|--------------|-------|-----|
| Abbr mismatch | Densify wrote Odds full names + heuristic abbrs (`BOCE`) while ingest uses canonical keys (`BOS`) | Join on **full name OR abbr aliases**; repaired **30/30** NBA `teams.abbr` |
| Date TZ skew | UTC `commence_time` can shift `games.game_date` vs ingest `gdte` (ET) | Match ET tip date **or** `game_date ± 1 day`; new densify stores ET calendar date |
| season_year | Calendar year split mid-season | NBA season start year (Aug–Jul) in `_ensure_hierarchy` |
| sport key | `basketball_nba` → `leagues.code='nba'` | Unchanged; inventory joins via `l.code='nba'` |

## Live Postgres inventory (truth)

| Metric | Value |
|--------|-------|
| `odds.mainline_games` | **1345** (owned; no re-densify) |
| `odds.odds_snapshot_rows` | **32698** |
| `nba_games_ingest` | **5583** |
| `nba_team_game_features` | **3794** |
| `nba_team_rolling_features` | **34** |
| `nba_market_projections` | **0** (offseason empty slate) |
| Abbr repair | scanned 30 / updated **30** |

## Odds API spend

| Item | Value |
|------|-------|
| Phase 1 densify | ~15k credits (retained) |
| Phase 2 densify | **skipped** |
| Floor policy | ≥1.5M remaining |

## Metrics (walkforward n=80, sims=1000, odds window)

| Metric | Phase 1 | Phase 2 |
|--------|---------|---------|
| Graded games | 60 | **80** |
| `n_with_close_lines` | **0** | **79** |
| Join misses | all | **1** |
| Model spread MAE | 14.26 | **12.64** |
| Model spread bias | -2.41 | -3.53 |
| Model total MAE | 17.28 | **14.98** |
| Model total bias | -5.97 | -2.01 |
| Close spread MAE | — | **12.21** |
| Close total MAE | — | **14.86** |
| Model ATS (vs actual) | 51.7% | **57.5%** |
| Model vs close ATS | — | **50.6%** |
| Blend hint | n/a | **hold** |
| Market blend weights | 0.25 / 0.25 | **0.40 / 0.45** (+ thin-sample boost) |
| Publish | research_only | **research_only** (ATS floor not cleared) |

## Letter grades

| Gate | Grade | Notes |
|------|-------|-------|
| Data ownership / densify discipline | **A** | Owned mainlines; no Phase-2 burn |
| Close-line join | **A** | 79/80; 30 teams abbr-repaired |
| Mainline calibration | **B-** | Near close MAE; vs-close ATS ~50.6% → research_only |
| Publish honesty | **A** | research_only mainlines + props; offseason empty |
| Nightly/beat pipeline | **B+** | `run_nba_daily_cycle` includes props materialize |
| Props projection integrity | **B** | Stub rates + env scale; no market nudge; O/U balance diagnostic |
| **Overall Phase 3** | **B+** | Full sim stack through research props board |

## Architecture

| Layer | Implementation |
|-------|----------------|
| Simulator | Possession MC + typed PBP events |
| Ingest | data.nba.com schedule + gamedetail |
| Features | `nba-rolling-gamelog-v1` |
| Close lines | Owned `odds_snapshots` via name/abbr/ET join |
| Publish | `nba_publish_policy` — PASS default |
| Props | `nba_player_prop_projection` + `nba_prop_edge_policy` |
| Nightly | context → sim → props → persist when slate exists |

## Phase exit criteria

| Criterion | Met? |
|-----------|------|
| Close-line join `n_with_close_lines >> 0` | **Y** (79/80) |
| Walkforward with real closes + blend tune | **Y** |
| Props board API + research tags | **Y** |
| Role-collapse Under refusal | **Y** |
| Nightly cycle includes props | **Y** |
| Canary phase3 | **Y** |

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/props/board
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-phase3-props-bootstrap'
```
