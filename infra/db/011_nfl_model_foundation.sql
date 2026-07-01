-- 011_nfl_model_foundation.sql
-- Initial NFL model tables mirroring MLB architecture.

CREATE TABLE IF NOT EXISTS nfl_game_context (
  game_id uuid PRIMARY KEY REFERENCES games(id) ON DELETE CASCADE,
  source text NOT NULL DEFAULT 'espn-scoreboard',
  offense_index_home numeric,
  offense_index_away numeric,
  defense_index_home numeric,
  defense_index_away numeric,
  rest_days_home numeric,
  rest_days_away numeric,
  context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_game_context_updated
  ON nfl_game_context (updated_at DESC);

CREATE TABLE IF NOT EXISTS nfl_market_projections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  model_version text NOT NULL,
  simulation_count int NOT NULL,
  home_win_prob numeric,
  away_win_prob numeric,
  total_mean numeric,
  spread_home numeric,
  fair_home_ml int,
  fair_away_ml int,
  projection jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_market_proj_game
  ON nfl_market_projections (game_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_market_proj_model
  ON nfl_market_projections (model_version, created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_market_outcomes (
  game_id uuid PRIMARY KEY REFERENCES games(id) ON DELETE CASCADE,
  actual_home_points int,
  actual_away_points int,
  final_total_points int,
  home_team_won boolean,
  source text NOT NULL DEFAULT 'espn-scoreboard',
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_market_outcomes_completed
  ON nfl_market_outcomes (completed_at DESC);
