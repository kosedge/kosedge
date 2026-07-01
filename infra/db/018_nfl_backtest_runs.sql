-- 018_nfl_backtest_runs.sql
-- Persist NFL walk-forward backtest runs and fold-level summaries.

CREATE TABLE IF NOT EXISTS nfl_model_backtest_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date date NOT NULL,
  model_version text NOT NULL,
  lookback_days integer NOT NULL,
  training_days integer NOT NULL,
  step_days integer NOT NULL,
  apply_calibration boolean NOT NULL DEFAULT true,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_model_backtest_runs_lookup
  ON nfl_model_backtest_runs (model_version, created_at DESC);
