-- 015_nfl_usage_features.sql
-- Normalized weekly usage + situational feature tables from nfl_dp_play_by_play.

CREATE TABLE IF NOT EXISTS nfl_dp_player_usage_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  position text,
  games_played int NOT NULL DEFAULT 0,
  involvement_plays int NOT NULL DEFAULT 0,
  targets int NOT NULL DEFAULT 0,
  receptions int NOT NULL DEFAULT 0,
  receiving_yards numeric NOT NULL DEFAULT 0,
  air_yards numeric NOT NULL DEFAULT 0,
  yards_after_catch numeric NOT NULL DEFAULT 0,
  rush_attempts int NOT NULL DEFAULT 0,
  rush_yards numeric NOT NULL DEFAULT 0,
  pass_attempts int NOT NULL DEFAULT 0,
  pass_yards numeric NOT NULL DEFAULT 0,
  pass_touchdowns int NOT NULL DEFAULT 0,
  red_zone_targets int NOT NULL DEFAULT 0,
  red_zone_carries int NOT NULL DEFAULT 0,
  goal_to_go_carries int NOT NULL DEFAULT 0,
  qb_dropbacks int NOT NULL DEFAULT 0,
  qb_pressures_taken int NOT NULL DEFAULT 0,
  touchdowns_scored int NOT NULL DEFAULT 0,
  first_downs_generated int NOT NULL DEFAULT 0,
  explosive_plays int NOT NULL DEFAULT 0,
  success_rate numeric,
  explosive_play_rate numeric,
  pressure_rate_allowed numeric,
  epa_per_involvement numeric,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_player_usage_weekly_player
  ON nfl_dp_player_usage_weekly (player_id, season, week);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_player_usage_weekly_team
  ON nfl_dp_player_usage_weekly (team, season, week);

CREATE TABLE IF NOT EXISTS nfl_dp_team_situational_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  games_played int NOT NULL DEFAULT 0,
  offensive_plays int NOT NULL DEFAULT 0,
  defensive_plays int NOT NULL DEFAULT 0,
  pass_plays int NOT NULL DEFAULT 0,
  run_plays int NOT NULL DEFAULT 0,
  early_down_plays int NOT NULL DEFAULT 0,
  early_down_pass_plays int NOT NULL DEFAULT 0,
  third_down_attempts int NOT NULL DEFAULT 0,
  third_down_conversions int NOT NULL DEFAULT 0,
  fourth_down_attempts int NOT NULL DEFAULT 0,
  fourth_down_conversions int NOT NULL DEFAULT 0,
  red_zone_plays int NOT NULL DEFAULT 0,
  red_zone_touchdowns int NOT NULL DEFAULT 0,
  sacks_allowed int NOT NULL DEFAULT 0,
  qb_hits_allowed int NOT NULL DEFAULT 0,
  sacks_generated int NOT NULL DEFAULT 0,
  qb_hits_generated int NOT NULL DEFAULT 0,
  explosive_pass_plays int NOT NULL DEFAULT 0,
  explosive_pass_allowed int NOT NULL DEFAULT 0,
  pass_rate numeric,
  early_down_pass_rate numeric,
  third_down_conversion_rate numeric,
  fourth_down_conversion_rate numeric,
  red_zone_td_rate numeric,
  pressure_rate_allowed numeric,
  pressure_rate_generated numeric,
  success_rate_offense numeric,
  success_rate_defense_allowed numeric,
  epa_per_play_offense numeric,
  epa_per_play_defense_allowed numeric,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_situational_weekly_team
  ON nfl_dp_team_situational_weekly (team, season, week);

CREATE OR REPLACE VIEW nfl_dp_player_usage_latest AS
SELECT DISTINCT ON (u.team, u.player_id)
  u.*
FROM nfl_dp_player_usage_weekly u
ORDER BY u.team, u.player_id, u.season DESC, u.week DESC;

CREATE OR REPLACE VIEW nfl_dp_team_situational_latest AS
SELECT DISTINCT ON (t.team)
  t.*
FROM nfl_dp_team_situational_weekly t
ORDER BY t.team, t.season DESC, t.week DESC;
