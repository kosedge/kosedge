# NBA Model — Enterprise Grade Report

**Generated:** 2026-07-31 (Phase 2)  
**Phase reached:** Phase 2 complete (close-line join + calibrate + publish posture)  
**Model version:** `nba-v1-poss-sim`  
**Worker canary:** `nba-poss-sim-20260731-phase2`  
**SHA:** `d6b9e26`  
**Railway CI:** [30672293540](https://github.com/kosedge/kosedge/actions/runs/30672293540) success  
**Vercel Production:** `dpl_FppfiCBjbRN3x4iUjzojXt8JyJkh` (Ready)  
**PR:** [#42](https://github.com/kosedge/kosedge/pull/42) (merged)

## Executive status

Phase 2 unblocked real calibration. Close-line join now lands **79/80** on the
walkforward sample (was **0**). Owned densified odds reused — **no Phase-2 Odds
API burn**. Publish posture stays **research_only** (model-vs-close ATS ~50.6%).
Props not published. NFL/MLB preserved. Offseason fair-lines stay empty/honest.

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
| Publish honesty | **A** | research_only; props queued; offseason empty |
| Nightly/beat pipeline | **B+** | `run_nba_daily_cycle` + 3am beat |
| **Overall Phase 2** | **B+** | Join blocker cleared; stake tags deferred |

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
| Close-line join `n_with_close_lines >> 0` | **Y** (79/80) |
| Walkforward with real closes + blend tune | **Y** (hint=hold) |
| Publish policy research_only / props queued | **Y** |
| Nightly/beat daily cycle | **Y** |
| Enterprise report + letter grades | **Y** |
| Canary phase2 + Railway + deploy-vercel | **Y** |

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-walkforward-sample?limit_games=80&simulations=1000'
```
