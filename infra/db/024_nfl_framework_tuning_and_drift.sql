-- 024_nfl_framework_tuning_and_drift.sql
-- Framework tuning artifacts and decomposition drift monitoring snapshots.

CREATE TABLE IF NOT EXISTS nfl_framework_tuning_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date date NOT NULL,
  model_version text NOT NULL,
  lookback_days int NOT NULL,
  training_days int NOT NULL,
  step_days int NOT NULL,
  candidate_count int NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  selected_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_framework_tuning_runs_model_created
  ON nfl_framework_tuning_runs (model_version, created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_framework_tuning_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES nfl_framework_tuning_runs(id) ON DELETE CASCADE,
  rank int NOT NULL,
  score numeric NOT NULL,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  candidate jsonb NOT NULL DEFAULT '{}'::jsonb,
  config_overrides jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_recommended boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_framework_tuning_candidates_run
  ON nfl_framework_tuning_candidates (run_id, rank ASC);

CREATE TABLE IF NOT EXISTS nfl_decomposition_drift_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_date date NOT NULL,
  model_version text NOT NULL,
  lookback_days int NOT NULL,
  baseline_weeks int NOT NULL,
  status text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_drift_snapshots_model_created
  ON nfl_decomposition_drift_snapshots (model_version, created_at DESC);
