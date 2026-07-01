-- 020_nfl_player_props_fantasy_foundation.sql
-- Enterprise NFL player projection, props, and fantasy foundation.

CREATE TABLE IF NOT EXISTS nfl_player_projection_features_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  position text,
  game_id text,
  opponent text,
  game_date date,
  snap_proxy numeric,
  route_proxy numeric,
  target_proxy numeric,
  rush_share numeric,
  red_zone_share numeric,
  qb_dropback_factor numeric,
  qb_pressure_factor numeric,
  team_pace_factor numeric,
  team_pass_rate_factor numeric,
  availability_confidence numeric NOT NULL DEFAULT 0.75,
  role_confidence numeric NOT NULL DEFAULT 0.65,
  feature_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  source text NOT NULL DEFAULT 'nfl_dp_usage_situational',
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_projection_features_lookup
  ON nfl_player_projection_features_weekly (season, week, position, team);

CREATE INDEX IF NOT EXISTS idx_nfl_player_projection_features_updated
  ON nfl_player_projection_features_weekly (updated_at DESC);

CREATE TABLE IF NOT EXISTS nfl_player_projection_baselines (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  position text,
  game_id text,
  model_version text NOT NULL,
  attempts_mean numeric,
  attempts_std numeric,
  carries_mean numeric,
  carries_std numeric,
  targets_mean numeric,
  targets_std numeric,
  completions_mean numeric,
  pass_yards_mean numeric,
  pass_yards_std numeric,
  rush_yards_mean numeric,
  rush_yards_std numeric,
  receiving_yards_mean numeric,
  receiving_yards_std numeric,
  receptions_mean numeric,
  receptions_std numeric,
  pass_tds_mean numeric,
  rush_tds_mean numeric,
  rec_tds_mean numeric,
  anytime_td_prob numeric,
  floor_outcome jsonb NOT NULL DEFAULT '{}'::jsonb,
  median_outcome jsonb NOT NULL DEFAULT '{}'::jsonb,
  ceiling_outcome jsonb NOT NULL DEFAULT '{}'::jsonb,
  uncertainty jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_coverage jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_projection_baselines_model
  ON nfl_player_projection_baselines (model_version, season DESC, week DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_player_projection_baselines_player
  ON nfl_player_projection_baselines (player_id, season DESC, week DESC);

CREATE TABLE IF NOT EXISTS nfl_player_prop_market_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  season int,
  week int,
  game_id uuid REFERENCES games(id) ON DELETE SET NULL,
  external_game_id text,
  sportsbook text NOT NULL,
  captured_at timestamptz NOT NULL,
  player_id text,
  player_name text NOT NULL,
  team text,
  opponent text,
  market_key text NOT NULL, -- pass_yds|rush_yds|rec_yds|receptions|anytime_td
  line numeric,
  over_price int,
  under_price int,
  implied_prob_over numeric,
  implied_prob_under numeric,
  source text NOT NULL DEFAULT 'odds_api',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_prop_market_snapshots_lookup
  ON nfl_player_prop_market_snapshots (season, week, market_key, team, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_player_prop_market_snapshots_game
  ON nfl_player_prop_market_snapshots (game_id, captured_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfl_player_prop_market_snapshots_key
  ON nfl_player_prop_market_snapshots (sportsbook, captured_at, player_name, market_key, COALESCE(line, -9999));

CREATE TABLE IF NOT EXISTS nfl_player_prop_model_edges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  season int NOT NULL,
  week int NOT NULL,
  model_version text NOT NULL,
  game_id uuid REFERENCES games(id) ON DELETE SET NULL,
  player_id text,
  player_name text NOT NULL,
  team text,
  market_key text NOT NULL,
  line numeric,
  model_mean numeric,
  model_std numeric,
  model_floor numeric,
  model_median numeric,
  model_ceiling numeric,
  over_prob numeric,
  under_prob numeric,
  fair_over_price int,
  fair_under_price int,
  market_over_price int,
  market_under_price int,
  edge_over numeric,
  edge_under numeric,
  confidence numeric NOT NULL DEFAULT 0.0,
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_prop_model_edges_board
  ON nfl_player_prop_model_edges (season, week, market_key, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_player_prop_model_edges_model
  ON nfl_player_prop_model_edges (model_version, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfl_player_prop_model_edges_key
  ON nfl_player_prop_model_edges (season, week, model_version, player_name, market_key, COALESCE(line, -9999));

CREATE TABLE IF NOT EXISTS nfl_fantasy_weekly_projections (
  season int NOT NULL,
  week int NOT NULL,
  scoring_profile text NOT NULL, -- standard|half_ppr|ppr
  model_version text NOT NULL,
  player_id text NOT NULL,
  player_name text NOT NULL,
  team text,
  position text,
  expected_points numeric NOT NULL,
  floor_points numeric,
  median_points numeric,
  ceiling_points numeric,
  rank_overall int,
  rank_position int,
  tier int,
  projection_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, scoring_profile, model_version, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_fantasy_weekly_projections_rank
  ON nfl_fantasy_weekly_projections (season, week, scoring_profile, position, rank_position);

CREATE TABLE IF NOT EXISTS nfl_projection_audit_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  season int NOT NULL,
  week int NOT NULL,
  layer text NOT NULL, -- player_features|player_baseline|props|fantasy
  model_version text NOT NULL,
  source_coverage jsonb NOT NULL DEFAULT '{}'::jsonb,
  freshness jsonb NOT NULL DEFAULT '{}'::jsonb,
  calibration_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
  readiness_status text NOT NULL DEFAULT 'warning',
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (season, week, layer, model_version, created_at)
);

CREATE INDEX IF NOT EXISTS idx_nfl_projection_audit_runs_lookup
  ON nfl_projection_audit_runs (season, week, layer, created_at DESC);
