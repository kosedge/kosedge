-- NBA Phase 3 player props foundation
ALTER TABLE nba_player_game_stubs
  ADD COLUMN IF NOT EXISTS fg3m DOUBLE PRECISION;

CREATE TABLE IF NOT EXISTS nba_player_prop_model_edges (
  model_version TEXT NOT NULL,
  as_of_date DATE NOT NULL,
  player_id TEXT NOT NULL,
  player_name TEXT,
  team_key TEXT,
  market_key TEXT NOT NULL,
  line DOUBLE PRECISION,
  model_mean DOUBLE PRECISION NOT NULL,
  model_std DOUBLE PRECISION NOT NULL,
  over_prob DOUBLE PRECISION,
  under_prob DOUBLE PRECISION,
  fair_over_price INTEGER,
  fair_under_price INTEGER,
  market_over_price INTEGER,
  market_under_price INTEGER,
  edge_over DOUBLE PRECISION,
  edge_under DOUBLE PRECISION,
  confidence DOUBLE PRECISION,
  diagnostics JSONB,
  worker_build_id TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (model_version, as_of_date, player_id, market_key)
);

CREATE INDEX IF NOT EXISTS idx_nba_player_prop_edges_date_tag
  ON nba_player_prop_model_edges (as_of_date DESC, market_key);
