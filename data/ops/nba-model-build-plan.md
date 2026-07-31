# NBA Model Build Plan

**Status:** Phase 2 — close-line join fix + calibrate + publish posture  
**Canary / worker_build_id:** `nba-poss-sim-20260731-phase2`  
**Default model version:** `nba-v1-poss-sim`  
**Prod web branch:** `deploy-vercel`  
**Model service:** Railway brave-art (`scripts/deploy-railway-model-service.sh` / GH Actions)

## Architecture (locked)

- Mirror NFL matchup sim + MLB pitch-by-pitch philosophy.
- **v1 = possession-level Monte Carlo** → ML / spread / total distributions.
- Typed **event-PBP interfaces** under the hood.
- No college props. No fake KEI. Props publish deferred to Phase 3.
- Odds: read owned `odds_snapshots` first; **targeted** historical densify only if NBA mainlines empty.

## Phase 0 — Scaffold (DONE)

Canary `nba-poss-sim-20260731-phase0b`.

## Phase 1 — Ingest + features (DONE)

| Deliverable | Notes |
|-------------|-------|
| data.nba.com ingest | 5583 games; features + rolling |
| Targeted densify | 1345 mainline games / 32,698 rows (~15k credits) |
| Thin walkforward | n=60; MAE weak; **`n_with_close_lines=0`** blocker |
| Canary | `nba-poss-sim-20260731-phase1` @ `778eede` |

## Phase 2 — Calibrate (THIS PASS)

| Deliverable | Location |
|-------------|----------|
| Close-line join fix | `_nba_market_lines_for_game` — ET tip date ±1 + full name / abbr aliases |
| Abbr repair | `repair_nba_odds_team_abbrs` |
| NBA season_year + ET game_date on densify | `_ensure_hierarchy` |
| Walkforward w/ real closes | `run_nba_walkforward_sample(prefer_odds_window=True)` |
| Market blend tune | defaults 0.40 / 0.45 + thin-sample boost; `blend_hint` from MAE ratio |
| Publish policy | `nba_publish_policy.py` — research_only PASS default |
| Nightly cycle | `run_nba_daily_cycle` + beat `run-nba-daily-cycle-3am` |
| Fair-lines honesty | phase2 + publish_posture; offseason empty |
| Canary | `nba-poss-sim-20260731-phase2` |

### Bootstrap (no Odds burn)

```bash
curl -sS -X POST 'https://model-service-production-e253.up.railway.app/api/jobs/run-nba-phase2-calibrate?walkforward_games=80&simulations=1000'
```

## Phase 3 — Props (ONLY after mainlines honest)

- Reuse NBA prop snapshots; role/minutes integrity; no cosmetic nudges.

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/nba/health
curl -sS https://model-service-production-e253.up.railway.app/nba/fair-lines
curl -sS https://model-service-production-e253.up.railway.app/nba/ops/inventory
cd services/model-service && python -m pytest tests/test_nba_*.py -q
```

## Constraints

- Research-first UI copy. Preserve NFL/MLB.
- Preserve DeploymentRecovery / BootShell / SportProShell.
- Do not burn large Odds API densify in Phase 2.
