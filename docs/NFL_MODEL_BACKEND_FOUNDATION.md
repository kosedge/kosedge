# NFL Model Backend Foundation

Initial NFL model foundation is now in `services/model-service`.

## Implemented

- NFL schedule/context ingestion task:
  - `src.tasks.pull_nfl_context_snapshot(days_ahead=14)`
- NFL simulation task:
  - `src.tasks.run_nfl_market_simulations(game_date=None, simulations=4000, model_version="nfl-v1.5-matchup-sim")`
- NFL historical pre-game projection backfill task (explicit as-of timestamps):
  - `src.tasks.backfill_nfl_historical_projections(start_date, end_date, simulations=4000, model_version="nfl-v1.5-matchup-sim", kickoff_buffer_minutes=30)`
- NFL outcomes ingestion task:
  - `src.tasks.pull_nfl_outcomes(days_back=60)`
- NFL grading task:
  - `src.tasks.run_nfl_quality_grading(lookback_days=60, model_version="nfl-v1.5-matchup-sim")`
- NFL walk-forward backtest task:
  - `src.tasks.run_nfl_walkforward_backtest(model_version="nfl-v1.5-matchup-sim", lookback_days=240, training_days=56, step_days=7, apply_calibration=true)`
- NFL champion/challenger promotion task:
  - `src.tasks.evaluate_nfl_model_promotion(challenger_model_version, lookback_days=45, auto_promote=true)`
- NFL API routes:
  - `GET /nfl/games?game_date=YYYY-MM-DD`
  - `GET /nfl/market-history?game_date=YYYY-MM-DD&market_code=moneyline|total`
  - `GET /nfl/clv-summary?model_version=nfl-v1.5-matchup-sim&lookback_days=45`
  - `GET /nfl/quality/latest?model_version=nfl-v1.5-matchup-sim&pipeline_stage=weekly_quality`
  - `GET /nfl/ops/backtest-runs?model_version=nfl-v1.5-matchup-sim&limit=20`
  - `GET /nfl/ops/backtest-report?model_version=nfl-v1.5-matchup-sim`
  - `GET /nfl/ops/active-model`
  - `GET /nfl/ops/promotion-events?limit=20`
  - `POST /nfl/ops/evaluate-promotion?challenger_model_version=nfl-v1.6-enterprise&lookback_days=45&auto_promote=true`
  - `GET /nfl/edges/today?model_version=nfl-v1.5-matchup-sim`
  - `GET /nfl/edges/optimize?...`
  - `GET /nfl/projections/players?season=2026&week=1&model_version=nfl-player-v1`
  - `GET /nfl/props/board?season=2026&week=1&model_version=nfl-player-v1`
  - `GET /nfl/fantasy/rankings?season=2026&week=1&scoring_profile=half_ppr&model_version=nfl-player-v1`
  - `GET /nfl/ops/projections-readiness?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /nfl/ops/materialize-player-baselines?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /nfl/ops/materialize-player-props?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /nfl/ops/materialize-fantasy?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /nfl/ops/run-player-cycle?season=2026&week=1&model_version=nfl-player-v1`
  - `GET /nfl/identity/queue?queue_status=pending`
  - `POST /nfl/identity/queue/{queue_id}/action?action=approve|reject&reviewer=...`
  - `POST /nfl/identity/refresh?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /nfl/identity/manual-reconciliations?limit=200`
  - `POST /nfl/identity/quality-snapshot?season=2026&week=1`
  - `GET /nfl/identity/quality/latest?season=2026&week=1`
  - `GET /nfl/features/player-usage?season=2025&week=1&team=BUF`
  - `GET /nfl/features/team-situational?season=2025&week=1&team=BUF`
  - `GET /nfl/features/team-rolling?season=2025&week=1&team=BUF`
  - `GET /nfl/features/matchup-pack?season=2025&week=1&home_team=BUF&away_team=NE&top_players=6`
  - `POST /nfl/simulations/{game_id}?simulations=4000&model_version=nfl-v1.5-matchup-sim`
- NFL readiness health:
  - `GET /health/nfl-production-readiness`
  - `GET /health/nfl-production-readiness/prometheus`
- NFL job endpoints:
  - `POST /api/jobs/pull-nfl-context?days_ahead=14`
  - `POST /api/jobs/run-nfl-simulations?game_date=YYYY-MM-DD&simulations=4000&model_version=nfl-v1.5-matchup-sim`
  - `POST /api/jobs/backfill-nfl-historical-projections?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&simulations=4000&model_version=nfl-v1.5-matchup-sim&kickoff_buffer_minutes=30`
  - `POST /api/jobs/materialize-nfl-market-history?lookback_days=45`
  - `POST /api/jobs/run-nfl-clv-attribution?lookback_days=45&model_version=nfl-v1.5-matchup-sim`
  - `POST /api/jobs/pull-nfl-outcomes?days_back=60`
  - `POST /api/jobs/run-nfl-quality-grading?lookback_days=60&model_version=nfl-v1.5-matchup-sim`
  - `POST /api/jobs/run-nfl-walkforward-backtest?model_version=nfl-v1.5-matchup-sim&lookback_days=240&training_days=56&step_days=7&apply_calibration=true`
  - `POST /api/jobs/evaluate-nfl-promotion?challenger_model_version=nfl-v1.6-enterprise&lookback_days=45&auto_promote=true`
  - `POST /api/jobs/run-nfl-player-baselines?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /api/jobs/pull-nfl-player-prop-markets?season=2026&week=1`
  - `POST /api/jobs/run-nfl-player-props?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /api/jobs/run-nfl-fantasy-projections?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /api/jobs/run-nfl-player-cycle?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /api/jobs/run-nfl-identity-refresh?season=2026&week=1&model_version=nfl-player-v1`
  - `POST /api/jobs/run-nfl-identity-manual-resolutions?limit=200&reviewer=...`
  - `POST /api/jobs/run-nfl-identity-quality-snapshot?season=2026&week=1`

## Data and tables

Migrations:

- `infra/db/011_nfl_model_foundation.sql`
- `infra/db/020_nfl_player_props_fantasy_foundation.sql`
- `infra/db/021_nfl_player_identity_graph.sql`

Tables:

- `nfl_game_context`
- `nfl_market_projections`
- `nfl_market_outcomes`
- `nfl_market_history_snapshots`
- `nfl_clv_attribution`
- `nfl_model_quality_snapshots`
- `nfl_model_backtest_runs`
- `nfl_model_runtime_state`
- `nfl_model_promotion_events`
- `nfl_portfolio_runs`
- `nfl_portfolio_recommendations`
- `nfl_dp_player_usage_weekly`
- `nfl_dp_team_situational_weekly`
- `nfl_dp_team_rolling_features_weekly`
- `nfl_dp_matchup_features_weekly`
- `nfl_player_projection_features_weekly`
- `nfl_player_projection_baselines`
- `nfl_player_prop_market_snapshots`
- `nfl_player_prop_model_edges`
- `nfl_fantasy_weekly_projections`
- `nfl_projection_audit_runs`
- `nfl_player_identities`
- `nfl_player_source_id_map`
- `nfl_player_aliases`
- `nfl_player_mapping_events`
- `nfl_player_mapping_review_queue`
- `nfl_player_mapping_quality_snapshots`

## Current model profile

- Model version: `nfl-v1.5-matchup-sim`
- Type: game-level Monte Carlo simulator
- Inputs:
  - offense/defense strength priors from team records
  - rest-day effects
  - home-field advantage
  - matchup/rolling feature-pack signals (`nfl_dp_matchup_features_weekly`) with bounded point adjustments and safe fallback-to-baseline when features are missing
  - totals-specific bounded signals:
    - tempo/pass-rate proxy
    - offense-vs-defense EPA interaction terms
    - success-rate interaction deltas
    - injury nowcast offense/defense multipliers and confidence-aware variance widening
- Outputs:
  - home/away win probabilities
  - implied fair moneylines
  - spread and calibrated total expectations
  - total distribution quantiles
  - explainability blocks in simulation diagnostics describing:
    - matchup feature adjustments
    - totals adjustments (component-level bounded contributions)
    - totals calibration (`base_total`, `calibrated_total`, `slope`, `intercept`, `sample_size`, `source`)

## Production hardening guardrails

- `GET /health/nfl-production-readiness` enforces hard go/no-go checks from latest `weekly_quality` snapshot:
  - minimum sample size
  - minimum calendar coverage
  - freshness (staleness days from last graded game)
  - max moneyline Brier
  - max total MAE
  - minimum CLV average
- Freshness policy is environment-driven and auditable in payload:
  - production default (`NFL_READINESS_MODE=production`): strict freshness gating
  - staging-only override (`NFL_READINESS_MODE=staging`): optional `NFL_READINESS_STAGING_MAX_LAST_GAME_AGE_DAYS` or `NFL_READINESS_STAGING_DISABLE_FRESHNESS_GATE=true`
  - payload includes `freshness_policy` (`mode`, `override_active`, `override_reason`, `freshness_gate_enabled`, `max_last_game_age_days_applied`)
- Non-ready responses return HTTP `503` with deterministic `gating_checks`, `reasons`, `freshness_policy`, and key metrics payload.
- Prometheus variant mirrors this status as `kosedge_nfl_production_readiness_ok`.

## Identity dependency and SLA gates

- Player props/fantasy pipelines now depend on canonical `player_uid` resolution, not free-form name joins.
- Resolver is deterministic and ordered:
  1. exact `source_system + external_id`
  2. exact normalized alias + team + position (+ season/week context)
  3. bounded fuzzy fallback with context and minimum score threshold
  4. ambiguity generates conflict queue item (no auto-map)
- Guardrail: trusted high-confidence links (`>= 0.95`) cannot be silently remapped.
- Weekly identity SLA snapshot (`nfl_player_mapping_quality_snapshots`) publishes:
  - `coverage_rate`
  - `high_confidence_auto_map_rate`
  - `unresolved_rate`
  - `conflict_rate`
  - `remap_count`
  - `reversal_count`
  - `source_freshness_hours`
  - `readiness_status`
- Publish gate for player props/fantasy:
  - `unresolved_rate <= 0.06`
  - `conflict_rate <= 0.02`
  - identity readiness must not be `no-go`.

## Walk-forward backtest

- `run_nfl_walkforward_backtest` uses strict eligibility before fold generation:
  - only points where `projection_created_at < outcome_completed_at` are eligible
  - ineligible rows are excluded before fold creation and scoring
- Historical backfill uses kickoff-relative timestamps (`created_at = kickoff - buffer`) so projections remain explicitly pre-outcome and auditable.
- Leakage checks are strict (`projection_created_at >= outcome_completed_at`), timezone-normalized, and reported via `leakage_violations`.
- Runs are persisted to `nfl_model_backtest_runs` with fold-level metrics and aggregate summary:
  - `base_brier_ml`, `calibrated_brier_ml`, `brier_improvement`
  - `base_mae_total_runs`, `calibrated_mae_total_runs`, `mae_improvement`
  - `leakage_violations`
  - per-fold totals calibrator coefficients (`total_calibration_slope`, `total_calibration_intercept`)
- Report reads:
  - `GET /nfl/ops/backtest-runs` (history)
  - `GET /nfl/ops/backtest-report` (latest summary + folds)

## NFL edge gating

- `GET /nfl/edges/today` computes model-vs-market edges and applies quality/confidence filtering by default.
- Default thresholds are env-configurable:
  - `NFL_EDGE_MIN_QUALITY_SCORE`
  - `NFL_EDGE_MIN_CONFIDENCE_SCORE`
  - `NFL_EDGE_MIN_ML_EDGE_PROB`
- Response includes diagnostics for production observability:
  - `filtered_count`
  - `filtered_reasons`

## Enterprise promotion framework

- Runtime champion state is persisted in `nfl_model_runtime_state` (`state_key=nfl_active_model`).
- Promotion evaluations are persisted in `nfl_model_promotion_events` with deterministic pass/fail gates and full payload snapshots.
- Hard promotion gates include:
  - minimum sample size
  - moneyline Brier improvement
  - total MAE improvement
  - CLV improvement trend
  - backtest sample + improvement minimums
  - drift guardrails (live-quality vs calibrated-backtest divergence caps)
- Auto-promotion only occurs when all gates pass **and** `NFL_AUTO_PROMOTE_ENABLED=true`; insufficient data never silently promotes.

## Injury/news nowcasting

- NFL simulation inputs now include injury-derived multipliers from `nfl_dp_injuries`.
- Nowcast logic applies bounded offense/defense adjustments per team with:
  - injury-status and practice-status severity mapping
  - positional impact weighting
  - freshness-aware confidence decay (half-life + stale floor guardrails)
- Applied in both:
  - API simulation path (`POST /nfl/simulations/{game_id}`)
  - scheduled/batch simulation path (`run_nfl_market_simulations`)
- Simulation diagnostics expose explainability fields for top injury drivers and confidence/freshness metadata.

## Portfolio optimizer

- `GET /nfl/edges/optimize` creates bankroll-aware stake recommendations from candidate NFL edges.
- Controls:
  - risk profiles (`conservative|balanced|aggressive`)
  - max exposure caps (total/game/team/time-window/player)
  - same-game/team/time-window correlation penalty
  - same-player and QB-WR stack penalties for player-level cards
  - bounded per-bet and total stake fractions
- Diagnostics include:
  - excluded count + reason buckets
  - exposure utilization by game/team/player/time-window
  - excluded examples with reason tags
  - final recommended stake fraction and amount
- Portfolio runs are auditable via `nfl_portfolio_runs` and `nfl_portfolio_recommendations`.

## Player projection and fantasy layer

- `materialize_nfl_player_baseline_projections` builds deterministic player-level weekly baselines from `nfl_player_projection_features_weekly`.
- Projection payload includes bounded mean/std, floor/median/ceiling outcomes, and per-player uncertainty metadata.
- `pull_nfl_player_prop_market_snapshots` integrates free `The Odds API` player props (`pass_yds`, `rush_yds`, `rec_yds`, `receptions`, `anytime_td`) into `nfl_player_prop_market_snapshots`.
- `materialize_nfl_player_props_edges` computes bounded model-vs-market edges with fallback behavior when market lines are missing.
- `materialize_nfl_fantasy_projections` transforms stat projections to `standard`, `half_ppr`, and `ppr`, including expected/floor/median/ceiling plus position/overall ranks and tiers.
- `nfl_projection_audit_runs` stores layer-level source coverage, freshness, calibration flags, and readiness state for player baseline/props/fantasy pipelines.

## Weekly quality metrics

`run_nfl_quality_grading` writes a `weekly_quality` payload to `nfl_model_quality_snapshots` with:

- `sample_size`: number of graded games with latest projection + completed outcome.
- `moneyline_brier`: probabilistic calibration/error for home-win probabilities (lower is better).
- `total_mae_base`: baseline absolute error on raw projected totals vs final totals (lower is better).
- `total_mae`: calibrated absolute error using bounded historical linear totals calibration (lower is better).
- `totals_calibration`: calibration metadata and market-substrate labeling (`historical-total-snapshots` vs `normalized-total-proxy`).
- `clv_avg` / `clv_positive_rate`: market efficiency signal from `nfl_clv_attribution`.
- `moneyline_hit_rate` / `total_hit_rate`: realized hit rate for recommended sides when outcome settle lines are available.
- `moneyline_positive_edge_hit_rate` / `total_positive_edge_hit_rate`: hit rates restricted to picks with positive CLV, useful as a CLV-style quality proxy.

Notes:
- Total hit rates use close line when present, otherwise open line.
- If any component is unavailable (e.g., no CLV rows in lookback), metrics are null-safe and return `null` with sample sizes preserved.
- NFL total market snapshots are normalized to half-points during history materialization for stable CLV and calibration targets.
