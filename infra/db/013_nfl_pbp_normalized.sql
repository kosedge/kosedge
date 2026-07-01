-- 013_nfl_pbp_normalized.sql
-- Materialized normalized play-by-play table for fast analytical queries.

CREATE TABLE IF NOT EXISTS nfl_dp_play_by_play (
  season int NOT NULL,
  week int,
  game_id text NOT NULL,
  play_id text NOT NULL,
  game_date date,
  game_day text,
  start_time text,
  home_team text,
  away_team text,
  posteam text,
  defteam text,
  play_type text,
  down int,
  ydstogo numeric,
  yardline_100 numeric,
  yards_gained numeric,
  passing_yards numeric,
  rushing_yards numeric,
  receiving_yards numeric,
  air_yards numeric,
  yards_after_catch numeric,
  passer_player_id text,
  passer_player_name text,
  receiver_player_id text,
  receiver_player_name text,
  rusher_player_id text,
  rusher_player_name text,
  complete_pass boolean,
  incomplete_pass boolean,
  interception boolean,
  touchdown boolean,
  first_down boolean,
  sack boolean,
  qb_hit boolean,
  fumble boolean,
  penalty boolean,
  epa numeric,
  wpa numeric,
  success boolean,
  score_differential numeric,
  play_description text,
  source text NOT NULL DEFAULT 'nflverse',
  object_key text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, game_id, play_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_pbp_posteam
  ON nfl_dp_play_by_play (posteam, season, week);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_pbp_passer
  ON nfl_dp_play_by_play (passer_player_name, season, game_date);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_pbp_receiver
  ON nfl_dp_play_by_play (receiver_player_name, season, game_date);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_pbp_rusher
  ON nfl_dp_play_by_play (rusher_player_name, season, game_date);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_pbp_game_day
  ON nfl_dp_play_by_play (game_day, season, game_date);
