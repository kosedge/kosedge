-- 014_nfl_market_intelligence.sql
-- NFL market-history and CLV attribution foundation.

CREATE TABLE IF NOT EXISTS nfl_market_history_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  captured_at timestamptz NOT NULL,
  sportsbook_code text NOT NULL,
  market_code text NOT NULL, -- moneyline | total
  home_price int,
  away_price int,
  total_points numeric,
  over_price int,
  under_price int,
  source text NOT NULL DEFAULT 'odds_snapshots',
  created_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (game_id, sportsbook_code, market_code, captured_at)
);

CREATE INDEX IF NOT EXISTS idx_nfl_market_history_game_time
  ON nfl_market_history_snapshots (game_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_market_history_market_time
  ON nfl_market_history_snapshots (market_code, captured_at DESC);

CREATE TABLE IF NOT EXISTS nfl_clv_attribution (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  projection_id uuid NOT NULL REFERENCES nfl_market_projections(id) ON DELETE CASCADE,
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  model_version text NOT NULL,
  market_code text NOT NULL, -- moneyline | total
  recommended_side text,      -- home | away | over | under
  open_line numeric,
  close_line numeric,
  model_line numeric,
  clv_value numeric,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (projection_id, market_code)
);

CREATE INDEX IF NOT EXISTS idx_nfl_clv_model_created
  ON nfl_clv_attribution (model_version, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_clv_game_created
  ON nfl_clv_attribution (game_id, created_at DESC);
