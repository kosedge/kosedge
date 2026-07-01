-- 012_nfl_data_platform.sql
-- Enterprise NFL data platform tables for multi-model consumption.

CREATE TABLE IF NOT EXISTS nfl_dp_ingestion_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  pipeline text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT NOW(),
  finished_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_message text
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_ingestion_runs_lookup
  ON nfl_dp_ingestion_runs (pipeline, started_at DESC);

CREATE TABLE IF NOT EXISTS nfl_dp_raw_objects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  object_type text NOT NULL,
  object_key text NOT NULL,
  season int,
  week int,
  game_id text,
  payload jsonb NOT NULL,
  checksum text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (source, object_type, object_key)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_raw_objects_lookup
  ON nfl_dp_raw_objects (object_type, season, week, ingested_at DESC);

CREATE TABLE IF NOT EXISTS nfl_dp_schedules (
  season int NOT NULL,
  week int,
  game_id text NOT NULL,
  game_date date,
  home_team text,
  away_team text,
  home_score int,
  away_score int,
  spread_line numeric,
  total_line numeric,
  location text,
  roof text,
  surface text,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, game_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_schedules_week
  ON nfl_dp_schedules (season, week, game_date);

CREATE TABLE IF NOT EXISTS nfl_dp_team_game_stats (
  season int NOT NULL,
  week int,
  game_id text NOT NULL,
  team text NOT NULL,
  opponent text,
  points_for numeric,
  points_against numeric,
  yards numeric,
  epa numeric,
  success_rate numeric,
  turnovers int,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, game_id, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_game_stats_team
  ON nfl_dp_team_game_stats (team, season, week);

CREATE TABLE IF NOT EXISTS nfl_dp_player_game_stats (
  season int NOT NULL,
  week int,
  game_id text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  team text,
  position text,
  stat_type text NOT NULL,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, game_id, player_id, stat_type)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_player_game_stats_team
  ON nfl_dp_player_game_stats (team, season, week);

CREATE TABLE IF NOT EXISTS nfl_dp_injuries (
  season int NOT NULL,
  week int,
  team text NOT NULL,
  player_key text NOT NULL,
  player_id text,
  player_name text,
  report_status text,
  practice_status text,
  injury text,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_key)
);

CREATE TABLE IF NOT EXISTS nfl_dp_rosters (
  season int NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  position text,
  jersey_number text,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, team, player_id)
);

CREATE OR REPLACE VIEW nfl_dp_team_features_latest AS
SELECT DISTINCT ON (t.team)
  t.team,
  t.season,
  t.week,
  t.points_for,
  t.points_against,
  t.yards,
  t.epa,
  t.success_rate,
  t.turnovers,
  t.updated_at
FROM nfl_dp_team_game_stats t
ORDER BY t.team, t.season DESC, t.week DESC, t.updated_at DESC;
