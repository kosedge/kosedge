# NFL Enterprise Sharpening Program

Goal: subscription-grade sides, totals, and props that stay honest under
walk-forward / nested holdouts — not a one-week leaderboard chase.

## What shipped in this program

### P0 — Injury role shocks + year cadence

- `nfl_injury_role_shocks.py`: report+practice → availability; OUT/DNP/IR
  players forfeit rush/target/QB share to healthy roommates.
- Feature SQL availability blends practice DNP/limited (not report-only).
- Weekly plan now includes **snap ingest** + **tendency rematerialize** before
  features (`inseason_weekly_update.py`).
- Celery Beat: `run-nfl-enterprise-weekly-sharpening` (Tue) +
  `run-nfl-walkforward-backtest-weekly` (Wed).
- Orchestrator: `scripts/nfl/run-weekly-inseason-update.sh`
- Season bootstrap: `scripts/nfl/bootstrap_enterprise_season_data.sh`

### P1 — Tendencies into live pricing

- `nfl_tendency_pricing.py`: PROE → bounded pass-rate factor for props;
  mild spread/total signals for `simulate_nfl_game`.
- Wired into `run_nfl_market_simulations` and baseline materialize
  (`tendency_pass_rate_factor` in `source_coverage`).

### P1 — Props calibration

- `prop-enterprise-cal-v1` pass intercept **−8.5**, stronger pass market shrink
  (base 0.32 / max 0.68). PLAY stake tags remain **research-only** until
  densified pass MAE ≤ 12.
- RB rush TD coeff soft-retuned to **0.092**.

### P2 — Market residual research path

- `nfl_prop_market_residual.py` + `scripts/nfl/prop_market_residual_holdout.py`
- Fits β on (model − line) → residual; evaluates unused holdout.
- Never flips `PLAY_STAKE_ELIGIBLE`.

### P3 — Desk health

- `nfl_prop_board_health.py`: snap coverage, injury feed, dual RB rooms,
  pass MAE gate for ops publish readiness.

## Year operating cadence

| When       | Job                                                                                       |
| ---------- | ----------------------------------------------------------------------------------------- |
| Tue ~04:15 | Weekly resilience (ingest / DR / freshness)                                               |
| Tue ~05:40 | Enterprise sharpening cycle (snaps, tendencies, rolling, features, baselines, box, props) |
| Wed ~08:20 | Sides/totals walkforward backtest                                                         |
| Thu ~07:08 | Player cycle (props markets + baselines)                                                  |
| Hourly     | Prop edges refresh                                                                        |
| Daily AM   | CLV attribution + market sims                                                             |

Set `NFL_PLAYER_CYCLE_WEEK` each week (finished real week) in worker env.

```bash
# One-time / offseason bootstrap
SEASONS=2024,2025,2026 ./scripts/nfl/bootstrap_enterprise_season_data.sh

# Every week after games grade
SEASON=2026 WEEK=5 ./scripts/nfl/run-weekly-inseason-update.sh

# Residual research (does not enable PLAY)
PYTHONPATH=services/model-service \
  .venv/bin/python scripts/nfl/prop_market_residual_holdout.py \
  --records data/ops/nfl-player-prop-vegas-benchmark/raw_prop_records.json
```

## Still blocked on paid / external feeds

These are real ceiling raises — code paths are ready to consume them:

1. **Official inactives** near kickoff (not in nflverse injuries alone).
2. **Low-latency depth + injury** (SportsDataIO / similar).
3. **Props continuity** (Sportradar or higher Odds API tier) for alt lines + CLV.
4. **Coverage / personnel / blitz** licensed PBP for matchup packs.

Until those land, the free stack (nflverse snaps+injuries+PBP+tendencies+market blend)
is the production path — sharpened, gated, and re-runnable every week.

## Honesty rules (non-negotiable)

1. No PLAY stake promotion without a **pre-registered unused holdout**.
2. Pass props stay research-only while densified MAE > 12.
3. Dual ≥1000-yard RB rooms on the same team are a desk red flag (`skill` quality JSON).
4. Market blend 0.30 on sides/totals stays; win by knowing _when_ to deviate.
