# WNBA Model Build Plan

**Status:** Phase 3 — player props research board live  
**Canary / worker_build_id:** `wnba-poss-sim-20260801-phase3`  
**Default model version:** `wnba-v1-poss-sim`  
**Props model version:** `wnba-player-props-v1`  
**Prod web branch:** `deploy-vercel`  
**Model service:** Railway (kosedge / brave-art)

## Sport-specific (NOT NBA copy-paste)

| Factor | WNBA | NBA |
|--------|------|-----|
| Game length | **40 min** (4×10) | 48 min |
| Pace | ~**80–82** poss/40 | ~100 poss/48 |
| Pace method | **Harmonic mean** (higher matchup volatility ~24%) | Arithmetic |
| ORtg/DRtg prior | ~**103** | ~114 |
| Home court | ~**2.0–2.5** (start 2.25) | ~2.5 |
| Teams | **13** (incl. GSV) | 30 |
| Season | Calendar tip year (May–Oct) | Oct–Jun split year |
| Abbr collisions | CHI/DAL/IND/MIN/PHX → `leagues.code='wnba'` | — |
| Props | pts/reb/ast/threes; higher usage concentration; role-collapse Under refuse | Same markets |

**Do not import NBA player priors or NBA pace defaults into WNBA sims.**

## Architecture

- Mirror NBA possession-sim stack with WNBA retune.
- v1 = possession-level Monte Carlo → ML / spread / total.
- Typed event-PBP interfaces under the hood.
- Props: minutes×usage stubs + team pace/ORtg; research_only.
- Odds: targeted densify only if mainline_games=0; leave ≥1.5M credits.

## Phase 0 — Scaffold (DONE)

Canary `wnba-poss-sim-20260801-phase0` → rolled into phase3 canary.

## Phase 1 — Ingest + features

| Deliverable | Notes |
|-------------|-------|
| data.wnba.com ingest | LeagueID=10 schedule + gamedetail |
| Fallbacks | SportsDataIO v3/wnba; ESPN scoreboard |
| Targeted densify | Cap credits; skip if mainline_games owned |
| Canary | `wnba-poss-sim-20260801-phase1` |

## Phase 2 — Calibrate

| Deliverable | Notes |
|-------------|-------|
| Close-line join | ET date ±1 + full name/abbr aliases (NBA BOCE→BOS lesson) |
| Walkforward | vs closes; market blend |
| Publish | research_only mainlines |
| Nightly | `run_wnba_daily_cycle` + beat |
| Canary | `wnba-poss-sim-20260801-phase2` |

## Phase 3 — Props

| Deliverable | Location |
|-------------|----------|
| Projection | `wnba_player_prop_projection.py` |
| Edge policy | `wnba_prop_edge_policy.py` (role-collapse Under refuse; stake_eligible=False) |
| API | `GET /wnba/props/board` |
| Jobs | `/api/jobs/run-wnba-phase3-props-bootstrap` |
| Web | `/pro/wnba/props` via `wnba-props-board.ts` |
| Canary | `wnba-poss-sim-20260801-phase3` |

### Bootstrap

```bash
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-wnba-phase1-bootstrap?max_credit_spend=200000'
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-wnba-phase2-calibrate'
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-wnba-phase3-props-bootstrap?lookback_games=8&limit_players=200'
curl -sS 'https://model-service-production-e253.up.railway.app/wnba/props/board'
```

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/wnba/health
curl -sS https://model-service-production-e253.up.railway.app/wnba/fair-lines
curl -sS https://model-service-production-e253.up.railway.app/wnba/props/board
curl -sS https://model-service-production-e253.up.railway.app/wnba/ops/inventory
cd services/model-service && python -m pytest tests/test_wnba_*.py -q
```

## Constraints

- Research-first. Preserve NFL/MLB/NBA.
- No college props.
- No stake-eligible PLAY until props holdout clears.
