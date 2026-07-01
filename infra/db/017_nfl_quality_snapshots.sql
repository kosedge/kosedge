-- 017_nfl_quality_snapshots.sql
-- Persisted quality snapshots for NFL model grading runs.

CREATE TABLE IF NOT EXISTS nfl_model_quality_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date date NOT NULL,
  model_version text NOT NULL,
  pipeline_stage text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_quality_snapshots_lookup
  ON nfl_model_quality_snapshots (model_version, pipeline_stage, created_at DESC);

