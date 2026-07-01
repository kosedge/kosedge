# MLB Model Backend Foundation

This document describes the initial MLB backend implementation inside `services/model-service`.

## Scope implemented now

- **Simulation engine (V1.1)**: PA-level run simulation for F5 and full game markets with lineup-confidence weighting, bullpen fatigue, and wind-direction effects.
- **Context ingestion job**: pulls MLB schedule, probable pitchers, umpire assignment, weather snapshot, park-factor priors, and bullpen load proxies.
- **Projection job**: runs simulations, stores fair market outputs, and writes simulation audit records.
- **Outcome ingestion job**: stores completed game outcomes for model calibration monitoring.
- **API routes**: list games/context/projections, run single-game simulation, and compute model-vs-market edges for MLB moneyline + totals.
- **Calibration route**: reports Brier/MAE and prediction-vs-realized drift over a lookback window.

## Model versioning

- Default model version: `mlb-v1-pa-sim`
- Designed for forward compatibility with pitch-level versions (e.g. `mlb-v2-pitch-sim`) without changing API shape.

## Database

Migration file:

- `infra/db/002_mlb_engine.sql`
- `infra/db/003_mlb_model_quality.sql`
- `infra/db/004_mlb_ops_snapshots.sql`
- `infra/db/005_mlb_model_governance.sql`
- `infra/db/006_mlb_premium_context.sql`
- `infra/db/007_mlb_reliever_tiers.sql`
- `infra/db/010_mlb_data_lake.sql`

Tables added:

- `mlb_game_context`
- `mlb_market_projections`
- `mlb_simulation_audit`
- `mlb_market_outcomes`

## Celery tasks

- `src.tasks.pull_mlb_context_snapshot(days_ahead=5)`
- `src.tasks.run_mlb_market_simulations(game_date=None, simulations=4000, model_version="mlb-v1-pa-sim")`
- `src.tasks.pull_mlb_outcomes(days_back=30)`
- `src.tasks.pull_mlb_data_lake_snapshot(days_back=45, days_ahead=7, ...)`
- `src.tasks.run_mlb_daily_cycle(...)`
- `src.tasks.evaluate_mlb_model_promotion(...)`
- `src.tasks.run_mlb_lineup_nowcast_repricing(...)`
- `src.tasks.run_mlb_walkforward_backtest(...)`
- `src.tasks.run_mlb_feature_ablation(...)`
- `src.tasks.run_mlb_determinism_check(...)`

## API endpoints

- `GET /mlb/games?game_date=YYYY-MM-DD`
- `POST /mlb/simulations/{game_id}?simulations=4000&model_version=mlb-v1-pa-sim`
- `GET /mlb/edges/today?model_version=mlb-v1-pa-sim`
- `GET /mlb/metrics/calibration?model_version=mlb-v1-pa-sim&lookback_days=30`
- `GET /mlb/metrics/version-compare?base_version=mlb-v1-pa-sim&challenger_version=mlb-v2-pitch-sim&lookback_days=30`
- `GET /mlb/markets/closing-lines?game_date=YYYY-MM-DD`
- `GET /mlb/metrics/clv?model_version=mlb-v1-pa-sim&lookback_days=30`
- `GET /mlb/edges/premium-feed?...`
- `GET /mlb/metrics/regime-calibration?...`
- `GET /mlb/ops/snapshots?limit=20`
- `GET /mlb/data-lake/raw-objects?...`
- `GET /mlb/data-lake/team-stats?...`
- `GET /mlb/data-lake/player-stats?...`
- `GET /mlb/ops/nowcast-runs?limit=30`
- `GET /mlb/ops/nowcast-confidence-drift?lookback_hours=24`
- `GET /mlb/ops/backtest-runs?limit=20`
- `GET /mlb/ops/model-card`
- `GET /mlb/ops/active-model`
- `POST /mlb/ops/active-model?model_version=...&reason=...`
- `GET /mlb/ops/alerts?limit=50`
- `GET /mlb/ops/go-no-go`

Job endpoints:

- `POST /api/jobs/pull-mlb-context?days_ahead=5`
- `POST /api/jobs/run-mlb-simulations?game_date=YYYY-MM-DD&simulations=4000&model_version=mlb-v1-pa-sim`
- `POST /api/jobs/pull-mlb-outcomes?days_back=30`
- `POST /api/jobs/pull-mlb-data-lake?days_back=60&days_ahead=7`
- `POST /api/jobs/run-mlb-daily-cycle?...`
- `POST /api/jobs/evaluate-mlb-promotion?...`
- `POST /api/jobs/mlb-lineup-nowcast-repricing?...`
- `POST /api/jobs/mlb-walkforward-backtest?...`
- `POST /api/jobs/mlb-feature-ablation?...`
- `POST /api/jobs/mlb-determinism-check?...`

## Design note

V1.1 is still intentionally stable while adding richer context and model-quality instrumentation. The pitch-by-pitch engine remains the next major upgrade and can re-use the same API and persistence contract.

## Pitch simulator feature flag

- Pitch-by-pitch simulation is gated by `MLB_ENABLE_PITCH_SIM`.
- To enable challenger runs, set:
  - `MLB_ENABLE_PITCH_SIM=true`
  - `model_version=mlb-v2-pitch-sim` (or a prefixed variant)

## Auto-promotion and alerts

- Enable automated promotion with:
  - `MLB_AUTO_PROMOTE_ENABLED=true`
- Promotion guardrails (env-configurable):
  - `MLB_PROMOTION_MIN_SAMPLE_SIZE` (default `120`)
  - `MLB_PROMOTION_MIN_CALENDAR_DAYS` (default `14`)
  - `MLB_PROMOTION_MAX_LAST_GAME_AGE_DAYS` (default `3`)
  - `MLB_PROMOTION_MIN_BRIER_IMPROVEMENT` (default `0.0020`)
  - `MLB_PROMOTION_MIN_MAE_IMPROVEMENT` (default `0.08`)
  - `MLB_PROMOTION_MIN_TOTAL_CLV_IMPROVEMENT` (default `0.0030`)
- Optional outbound alert webhook:
  - `MLB_ALERT_WEBHOOK_URL=https://...`
- Lineup nowcast repricing cadence knobs:
  - `MLB_NOWCAST_HORIZON_HOURS` (default `18`)
  - `MLB_NOWCAST_SIM_COUNT` (default `2500`)
- Leakage/calibration governance knobs:
  - `MLB_ALLOW_HISTORICAL_SIM` (default `false`)
  - `MLB_MAX_ACCEPTABLE_ECE` (default `0.06`)
  - `MLB_RUN_DAILY_BACKTEST` (default `false`)
  - `MLB_RUN_DAILY_DETERMINISM_CHECK` (default `true`)
  - `MLB_RUN_DAILY_ABLATION` (default `false`)
- Data-lake ingestion knobs:
  - `MLB_RUN_DAILY_DATA_LAKE` (default `true`)
  - `MLB_DATA_LAKE_DAYS_BACK` (default `60`)
  - `MLB_DATA_LAKE_DAYS_AHEAD` (default `7`)
  - `MLB_DATA_LAKE_INCLUDE_ROSTERS` (default `true`)
  - `MLB_DATA_LAKE_INCLUDE_GAME_FEEDS` (default `true`)

## Recommended weekend runbook

- Run migrations `002`, `003`, `004`, `005`, `006`, `007`.
- Kick daily pipeline manually first:
  - `POST /api/jobs/run-mlb-daily-cycle`
- Trigger promotion evaluation manually (optional):
  - `POST /api/jobs/evaluate-mlb-promotion`
- Verify outputs:
  - `GET /mlb/metrics/calibration`
  - `GET /mlb/metrics/version-compare`
  - `GET /mlb/metrics/clv`
  - `GET /mlb/edges/premium-feed`
  - `GET /mlb/ops/snapshots`
  - `GET /mlb/ops/active-model`
  - `GET /mlb/ops/alerts`
  - `GET /mlb/ops/go-no-go`

## Premium-model differentiators implemented

- Bullpen availability signal (separate from fatigue) in context + simulations.
- High-leverage reliever availability tier signal (separate from bulk availability).
- Starter identity priors (quality/K/BB/GB proxies) for probable starters.
- Uncertainty-aware outputs:
  - moneyline probability confidence intervals
  - total-run distribution bands (p10 / p50 / p90)
- Explainability drivers included in simulation diagnostics and edge payload.
- Weighted market consensus (book-quality weighted, trimmed outlier handling) for edge detection.
- No-vig synthetic market-maker probability baseline for moneyline edge evaluation.
- Premium feed endpoint with quality scoring, stake sizing, and one-play-per-game diversification.
- Dynamic confidence decay based on context freshness latency.
- Premium feed risk profiles (`conservative|balanced|aggressive`) with bankroll-aware stake amounts.
