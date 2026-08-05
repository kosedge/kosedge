-- 049_cfb_performance_tracking.sql
-- CFB season-engine projection logs for continuous performance + CLV tracking.
-- Standalone (no FK to games) — project-game keys are season/week/teams until
-- a CFB schedule table is wired. JSONL lake is the durable fallback when
-- Postgres is unreachable.

CREATE TABLE IF NOT EXISTS cfb_projection_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_key text NOT NULL,
  season int NOT NULL,
  week int NOT NULL,
  home_team text NOT NULL,
  away_team text NOT NULL,
  engine_version text NOT NULL,
  projected_at timestamptz NOT NULL DEFAULT NOW(),
  model_spread_home numeric,
  model_total numeric,
  home_win_prob numeric,
  away_win_prob numeric,
  expected_home_score numeric,
  expected_away_score numeric,
  drivers jsonb NOT NULL DEFAULT '{}'::jsonb,
  projection jsonb NOT NULL DEFAULT '{}'::jsonb,
  close_spread_home numeric,
  close_total numeric,
  close_captured_at timestamptz,
  close_source text,
  spread_clv numeric,
  total_clv numeric,
  home_score int,
  away_score int,
  result_captured_at timestamptz,
  result_source text,
  grade_ats text,
  grade_ou text,
  grade_su text,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cfb_proj_logs_projected
  ON cfb_projection_logs (projected_at DESC);

CREATE INDEX IF NOT EXISTS idx_cfb_proj_logs_game_key
  ON cfb_projection_logs (game_key, projected_at DESC);

CREATE INDEX IF NOT EXISTS idx_cfb_proj_logs_version
  ON cfb_projection_logs (engine_version, projected_at DESC);

CREATE INDEX IF NOT EXISTS idx_cfb_proj_logs_season_week
  ON cfb_projection_logs (season, week);
