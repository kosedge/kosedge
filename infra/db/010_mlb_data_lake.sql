-- 010_mlb_data_lake.sql
-- Shared MLB data lake tables so multiple models can consume the same canonical datasets.

CREATE TABLE IF NOT EXISTS mlb_raw_data_objects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  object_type text NOT NULL,
  object_key text NOT NULL,
  as_of_date date NOT NULL,
  payload jsonb NOT NULL,
  checksum text NOT NULL,
  fetched_at timestamptz NOT NULL DEFAULT NOW(),
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (source, object_type, object_key, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_mlb_raw_data_objects_lookup
  ON mlb_raw_data_objects (object_type, as_of_date DESC, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_mlb_raw_data_objects_source
  ON mlb_raw_data_objects (source, object_type, updated_at DESC);

CREATE TABLE IF NOT EXISTS mlb_team_daily_stats (
  as_of_date date NOT NULL,
  season int NOT NULL,
  team_id int NOT NULL,
  team_name text,
  offense_index numeric,
  offense_split_vs_l numeric,
  offense_split_vs_r numeric,
  recent_form_index numeric,
  wins int,
  losses int,
  run_diff int,
  source text NOT NULL DEFAULT 'mlb-stats-api',
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (as_of_date, season, team_id)
);

CREATE INDEX IF NOT EXISTS idx_mlb_team_daily_stats_season
  ON mlb_team_daily_stats (season, as_of_date DESC);

CREATE TABLE IF NOT EXISTS mlb_player_daily_stats (
  as_of_date date NOT NULL,
  season int NOT NULL,
  player_id int NOT NULL,
  player_name text,
  team_id int,
  stat_group text NOT NULL,
  split_key text NOT NULL DEFAULT 'all',
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  source text NOT NULL DEFAULT 'mlb-stats-api',
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (as_of_date, season, player_id, stat_group, split_key)
);

CREATE INDEX IF NOT EXISTS idx_mlb_player_daily_stats_team
  ON mlb_player_daily_stats (team_id, as_of_date DESC);

CREATE INDEX IF NOT EXISTS idx_mlb_player_daily_stats_group
  ON mlb_player_daily_stats (stat_group, as_of_date DESC);
