-- 025_nfl_launch_hardening.sql
-- Launch hardening audit trail, runtime config locks, and backup manifests.

CREATE TABLE IF NOT EXISTS nfl_pipeline_stage_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id uuid NOT NULL,
  pipeline text NOT NULL,
  stage text NOT NULL,
  status text NOT NULL DEFAULT 'running',
  started_at timestamptz NOT NULL DEFAULT NOW(),
  finished_at timestamptz,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_pipeline_stage_runs_cycle
  ON nfl_pipeline_stage_runs (cycle_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_nfl_pipeline_stage_runs_stage
  ON nfl_pipeline_stage_runs (pipeline, stage, created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_runtime_config_locks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version text NOT NULL,
  lock_key text NOT NULL,
  framework_version text NOT NULL,
  selected_tuning_run_id uuid,
  config_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  lock_reason text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (model_version, lock_key)
);

CREATE INDEX IF NOT EXISTS idx_nfl_runtime_config_locks_active
  ON nfl_runtime_config_locks (model_version, is_active, created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_data_ownership_backups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  backup_key text NOT NULL UNIQUE,
  artifact_dir text,
  manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_data_ownership_backups_created
  ON nfl_data_ownership_backups (created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_launch_readiness_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id uuid,
  model_version text NOT NULL,
  status text NOT NULL,
  checks jsonb NOT NULL DEFAULT '{}'::jsonb,
  blockers jsonb NOT NULL DEFAULT '[]'::jsonb,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_launch_readiness_reports_lookup
  ON nfl_launch_readiness_reports (model_version, created_at DESC);
