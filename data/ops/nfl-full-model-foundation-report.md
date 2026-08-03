# Full NFL Model: Foundation + Player Box Scores

**Branch:** `nfl-full-model-foundation` → `deploy-vercel` (merged #71)  
**Engine version:** `nfl-season-engine-v1.1-calibrated` (see `nfl-season-engine-calibration-20260803.md`)  
**Date:** 2026-08-03  
**Status:** Working structure + path-coherent season sim + future-game player boxes. **Calibration pass applied** (efficiency baselines, residual usage bucket, scoring/HFA alignment, softened strength evolution).

## Goal (this pass)

Hierarchical season simulation that can:

1. Simulate a full NFL season (~272 games) many times with path coherence
2. Project skill-player box-score distributions for any future game
3. Keep team/player totals consistent within a sim path

## Architecture (four layers)

| Layer | Module | Responsibility | Real vs placeholder |
| --- | --- | --- | --- |
| 1 Team strength | `team_strength.py` | O/D indices; evolve across a sim path | **Real** when loaded via `_load_team_strength_priors` (EPA). **Placeholder** mean-reverting path evolution. |
| 2 Game script | `game_script.py` | Pace, total, win prob, lead/trail/neutral | Analytic from Layer 1 (thin). Not a rewrite of `simulate_nfl_game`. |
| 3 Player usage | `player_usage.py` | Targets, carries, routes, snap share \| script + role | **Real** identities from `nfl_dp_depth_chart_weekly` when DB available. Script tilts are thin priors. |
| 4 Production | `production.py` | Usage + matchup + script → yards/TDs/receptions/INTs | Efficiency priors from roles; INT rate is thin league-ish (projection engine has no INT mean yet). |

Package root: `services/model-service/src/services/nfl_season_engine/`

Orchestration:

- `season_sim.py` — N path-coherent full seasons
- `game_query.py` — single future-game Monte Carlo boxes
- `loaders.py` — DB universe or offline demo universe

## Entry points

```bash
# Offline demo (no DB)
python scripts/nfl/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game BUF@KC

# DB-backed (DATABASE_URL set)
python scripts/nfl/run_hierarchical_season_sim.py --season 2026 --n-sims 100
```

HTTP (additive on model-service; does **not** touch Edge Board / Model-vs-KEI #70):

- `GET  /nfl/season-engine/status`
- `POST /nfl/season-engine/simulate?n_sims=25&season=2026`
- `GET  /nfl/season-engine/game-boxes?home_team=KC&away_team=BUF&week=1&n_replicates=400`

Tests: `services/model-service/tests/test_nfl_season_engine.py`

## What works now

- Full-season path sim: 272 games × N sims; wins sum to 272 per path
- Strengths evolve inside a path (hot/cold drift + mean reversion)
- Future-game query returns point estimates + p10/p50/p90 distributions for:
  - QB: pass yds, pass TDs, INTs, rush yds
  - RB: rush yds, rush TDs, rec yds, receptions
  - WR/TE: rec yds, receptions, rec TDs
- Transparent notes on every artifact (real vs placeholder sources)
- Additive APIs — existing market sim / props / Edge Board paths unchanged

## Intentionally thin

- Strength evolution gains (not Bayesian / not backtested)
- Game script analytic (not hooked into `simulate_nfl_game` replicate loop)
- INT rates, efficiency CVs, script tilts
- Demo schedule is round-robin when DB schedule unavailable
- Demo / default efficiency priors when baselines not wired into roles

## Relationship to existing code

| Existing | Role vs this engine |
| --- | --- |
| `simulate_2026_season.py` | Bernoulli win-totals / futures MC — **unchanged** |
| `nfl_simulator.simulate_nfl_game` | Live Edge Board score markets — **unchanged** |
| `nfl_player_box_score_simulator` | Per-game prop box MC from baselines — complementary; this engine owns season-path coherence |
| `nfl_player_projection_engine` | Deterministic means for props — reused conceptually for efficiency shape |

## Sample future-game projection (demo) — post calibration

Artifact: `data/ops/nfl-season-engine-calibration-after/`  
Full write-up: `data/ops/nfl-season-engine-calibration-20260803.md`  
Matchup: **BUF @ KC**, week 1, 300 replicates (demo universe, seed 2026).

Game script summary:

- home_win_prob ≈ 0.53
- expected_total ≈ 46.6
- pace_plays ≈ 63.6 / team

| Team | Pos | Player | Point estimate (calibrated) |
| --- | --- | --- | --- |
| KC | QB | P.Mahomes | pass 247 / TD 1.52 / INT 0.57 / rush 8 |
| BUF | QB | J.Allen | pass 229 / TD 1.43 / INT 0.61 / rush 21 |
| BUF | RB | J.Cook | rush 59 / TD 0.39 / rec 19 / 2.6 |
| KC | WR | R.Rice | rec 56 / 5.3 / TD 0.32 |
| KC | RB | I.Pacheco | rush 54 / TD 0.37 / rec 17 / 2.4 |
| KC | TE | T.Kelce | rec 42 / 4.1 / TD 0.24 |

## Remaining gaps

1. Optional hook of Layer 2 into `simulate_nfl_game` replicate margins (documented v2 in box-score sim)
2. Historical walk-forward calibration of strength evolution + script tilts (beyond league priors)
3. Injury / availability shocks inside season paths
4. Persist season-engine artifacts to a stable hub path (optional web surfacing)
5. Heavier production runs (1k–10k season paths) via CLI / worker, not HTTP
6. Role-specific QB rush volume (Allen still light vs career)

## Railway

New routes live on model-service. Deploy the `kosedge` Railway service from this branch (or after merge to the Railway tracking branch) if live HTTP queries are required. Local/CLI demo works without Railway.
