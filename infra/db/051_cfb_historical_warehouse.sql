-- 051_cfb_historical_warehouse.sql
-- CFB research warehouse metadata (v1). Bulk PBP/history stays on HD parquet.
-- Production season-engine does not live-query these tables per request.

CREATE TABLE IF NOT EXISTS cfb_wh_ingestion_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  pipeline text NOT NULL DEFAULT 'cfb_historical_warehouse_v1',
  started_at timestamptz NOT NULL DEFAULT NOW(),
  finished_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_message text
);

CREATE TABLE IF NOT EXISTS cfb_wh_teams (
  team_id text PRIMARY KEY,
  espn_abbr text,
  display_name text,
  conference_source text NOT NULL DEFAULT 'packaged_2026_approx',
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cfb_wh_team_aliases (
  alias text NOT NULL,
  team_id text NOT NULL REFERENCES cfb_wh_teams (team_id),
  kind text NOT NULL,
  season int NOT NULL DEFAULT 0,
  PRIMARY KEY (alias, kind, season)
);

CREATE TABLE IF NOT EXISTS cfb_wh_games (
  game_id text NOT NULL,
  season int NOT NULL,
  week int,
  game_date date,
  kickoff timestamptz,
  home_team_id text NOT NULL,
  away_team_id text NOT NULL,
  home_espn_id text,
  away_espn_id text,
  fcs_home boolean NOT NULL DEFAULT false,
  fcs_away boolean NOT NULL DEFAULT false,
  fcs_opponent boolean NOT NULL DEFAULT false,
  neutral boolean NOT NULL DEFAULT false,
  home_score int,
  away_score int,
  era_tag text,
  source text NOT NULL DEFAULT 'sportsdataverse_espn',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, game_id)
);

CREATE INDEX IF NOT EXISTS idx_cfb_wh_games_week
  ON cfb_wh_games (season, week, game_date);

CREATE TABLE IF NOT EXISTS cfb_wh_odds_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id text NOT NULL,
  season int NOT NULL,
  captured_at timestamptz,
  available_at timestamptz,
  book text,
  market text NOT NULL,
  spread_home numeric,
  total_points numeric,
  price_home numeric,
  price_away numeric,
  source text NOT NULL,
  snapshot_kind text NOT NULL DEFAULT 'close_ish'
);

CREATE INDEX IF NOT EXISTS idx_cfb_wh_odds_game
  ON cfb_wh_odds_snapshots (season, game_id, captured_at);

CREATE TABLE IF NOT EXISTS cfb_wh_closing_lines (
  game_id text NOT NULL,
  season int NOT NULL,
  week int,
  home_team_id text,
  away_team_id text,
  close_spread_home numeric,
  close_total numeric,
  close_ml_home numeric,
  close_ml_away numeric,
  open_spread_home numeric,
  open_total numeric,
  book text,
  source text NOT NULL,
  line_fidelity text,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, game_id)
);

CREATE TABLE IF NOT EXISTS cfb_wh_feature_registry (
  feature_name text PRIMARY KEY,
  available_at_rule text NOT NULL DEFAULT 'strictly_before_kickoff',
  notes text,
  registered_at timestamptz NOT NULL DEFAULT NOW()
);

INSERT INTO cfb_wh_feature_registry (feature_name, notes)
VALUES (
  'model_fair_placeholder',
  'Skeleton backtest fairs must stamp available_at strictly before kickoff.'
)
ON CONFLICT (feature_name) DO NOTHING;
