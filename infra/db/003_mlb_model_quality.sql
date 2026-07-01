-- 003_mlb_model_quality.sql
-- Additional MLB context features + quality tracking tables.

ALTER TABLE mlb_game_context
  ADD COLUMN IF NOT EXISTS lineup_confidence_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS lineup_confidence_away numeric(6,4),
  ADD COLUMN IF NOT EXISTS bullpen_fatigue_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS bullpen_fatigue_away numeric(6,4),
  ADD COLUMN IF NOT EXISTS bullpen_ip_last3_home numeric(6,3),
  ADD COLUMN IF NOT EXISTS bullpen_ip_last3_away numeric(6,3),
  ADD COLUMN IF NOT EXISTS umpire_run_factor numeric(6,4);

CREATE TABLE IF NOT EXISTS mlb_simulation_audit (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  model_version text NOT NULL,
  simulation_count int NOT NULL,
  random_seed bigint,
  inputs jsonb,
  run_rates jsonb,
  diagnostics jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_sim_audit_game_created
  ON mlb_simulation_audit (game_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mlb_sim_audit_model_created
  ON mlb_simulation_audit (model_version, created_at DESC);

CREATE TABLE IF NOT EXISTS mlb_market_outcomes (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  actual_home_runs int NOT NULL,
  actual_away_runs int NOT NULL,
  final_total_runs int NOT NULL,
  home_team_won boolean NOT NULL,
  source text NOT NULL DEFAULT 'mlb-stats-api',
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (game_id)
);

CREATE INDEX IF NOT EXISTS idx_mlb_market_outcomes_completed
  ON mlb_market_outcomes (completed_at DESC);
