-- 004_mlb_ops_snapshots.sql
-- Persist daily MLB model operations + quality snapshots.

CREATE TABLE IF NOT EXISTS mlb_model_run_snapshots (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_date date NOT NULL,
  model_version text NOT NULL,
  pipeline_stage text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_model_run_snapshots_lookup
  ON mlb_model_run_snapshots (run_date DESC, model_version, pipeline_stage, created_at DESC);
