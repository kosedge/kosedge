-- 047_wnba_model_foundation.sql
-- WNBA possession-sim model foundation (Phase 0–3).
-- Idempotent; mirrors ensure_wnba_model_tables() in model-service.
-- Sport-scoped: leagues.code='wnba' — CHI/DAL/IND/MIN/PHX collide with NBA.

CREATE TABLE IF NOT EXISTS wnba_model_runtime_state (
  state_key TEXT PRIMARY KEY,
  active_model_version TEXT NOT NULL,
  previous_model_version TEXT,
  reason TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wnba_game_context (
  game_id TEXT PRIMARY KEY,
  pace_home DOUBLE PRECISION,
  pace_away DOUBLE PRECISION,
  ortg_home DOUBLE PRECISION,
  ortg_away DOUBLE PRECISION,
  drtg_home DOUBLE PRECISION,
  drtg_away DOUBLE PRECISION,
  three_pt_rate_home DOUBLE PRECISION,
  three_pt_rate_away DOUBLE PRECISION,
  three_pt_pct_home DOUBLE PRECISION,
  three_pt_pct_away DOUBLE PRECISION,
  rest_days_home DOUBLE PRECISION,
  rest_days_away DOUBLE PRECISION,
  sample_games_home INTEGER,
  sample_games_away INTEGER,
  feature_pack_version TEXT,
  context JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wnba_market_projections (
  id BIGSERIAL PRIMARY KEY,
  game_id TEXT NOT NULL,
  model_version TEXT NOT NULL,
  simulation_count INTEGER NOT NULL,
  home_win_prob DOUBLE PRECISION,
  total_mean DOUBLE PRECISION,
  margin_mean DOUBLE PRECISION,
  fair_home_ml INTEGER,
  fair_total DOUBLE PRECISION,
  fair_spread_home DOUBLE PRECISION,
  home_cover_prob DOUBLE PRECISION,
  worker_build_id TEXT,
  projection JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wnba_market_projections_game_created
  ON wnba_market_projections (game_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_wnba_market_projections_model_created
  ON wnba_market_projections (model_version, created_at DESC);

CREATE TABLE IF NOT EXISTS wnba_team_rolling_features (
  team_key TEXT NOT NULL,
  as_of_date DATE NOT NULL,
  window_games INTEGER NOT NULL DEFAULT 10,
  pace DOUBLE PRECISION,
  ortg DOUBLE PRECISION,
  drtg DOUBLE PRECISION,
  three_pt_rate DOUBLE PRECISION,
  three_pt_pct DOUBLE PRECISION,
  two_pt_pct DOUBLE PRECISION,
  ft_rate DOUBLE PRECISION,
  ft_pct DOUBLE PRECISION,
  to_rate DOUBLE PRECISION,
  orb_rate DOUBLE PRECISION,
  sample_games INTEGER,
  feature_pack_version TEXT,
  payload JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (team_key, as_of_date, window_games)
);

CREATE INDEX IF NOT EXISTS idx_wnba_team_rolling_as_of
  ON wnba_team_rolling_features (as_of_date DESC, team_key);

CREATE TABLE IF NOT EXISTS wnba_possessions (
  id BIGSERIAL PRIMARY KEY,
  external_game_id TEXT NOT NULL,
  possession_index INTEGER NOT NULL,
  offense_team_key TEXT,
  defense_team_key TEXT,
  points INTEGER,
  ended_by TEXT,
  period INTEGER,
  clock_seconds DOUBLE PRECISION,
  events JSONB,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (external_game_id, possession_index, source)
);

CREATE INDEX IF NOT EXISTS idx_wnba_possessions_game
  ON wnba_possessions (external_game_id);

CREATE TABLE IF NOT EXISTS wnba_games_ingest (
  external_game_id TEXT PRIMARY KEY,
  game_date DATE,
  start_time TIMESTAMPTZ,
  home_team_key TEXT,
  away_team_key TEXT,
  home_score INTEGER,
  away_score INTEGER,
  status TEXT,
  season TEXT,
  source TEXT,
  raw JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wnba_games_ingest_date
  ON wnba_games_ingest (game_date DESC);

CREATE INDEX IF NOT EXISTS idx_wnba_games_ingest_season
  ON wnba_games_ingest (season, game_date);

CREATE TABLE IF NOT EXISTS wnba_team_game_features (
  external_game_id TEXT NOT NULL,
  team_key TEXT NOT NULL,
  game_date DATE NOT NULL,
  is_home BOOLEAN,
  opponent_key TEXT,
  pace DOUBLE PRECISION,
  ortg DOUBLE PRECISION,
  drtg DOUBLE PRECISION,
  three_pt_rate DOUBLE PRECISION,
  three_pt_pct DOUBLE PRECISION,
  two_pt_pct DOUBLE PRECISION,
  ft_rate DOUBLE PRECISION,
  ft_pct DOUBLE PRECISION,
  to_rate DOUBLE PRECISION,
  orb_rate DOUBLE PRECISION,
  points DOUBLE PRECISION,
  possessions DOUBLE PRECISION,
  rest_days DOUBLE PRECISION,
  season TEXT,
  source TEXT,
  payload JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (external_game_id, team_key)
);

CREATE INDEX IF NOT EXISTS idx_wnba_team_game_features_team_date
  ON wnba_team_game_features (team_key, game_date DESC);

CREATE TABLE IF NOT EXISTS wnba_player_game_stubs (
  external_game_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  player_name TEXT,
  team_key TEXT,
  game_date DATE,
  minutes DOUBLE PRECISION,
  usage_proxy DOUBLE PRECISION,
  pts DOUBLE PRECISION,
  reb DOUBLE PRECISION,
  ast DOUBLE PRECISION,
  fg3m DOUBLE PRECISION,
  fga DOUBLE PRECISION,
  fta DOUBLE PRECISION,
  tov DOUBLE PRECISION,
  source TEXT,
  payload JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (external_game_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_wnba_player_game_stubs_team_date
  ON wnba_player_game_stubs (team_key, game_date DESC);

CREATE TABLE IF NOT EXISTS wnba_player_prop_model_edges (
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

CREATE INDEX IF NOT EXISTS idx_wnba_player_prop_edges_date_tag
  ON wnba_player_prop_model_edges (as_of_date DESC, market_key);
