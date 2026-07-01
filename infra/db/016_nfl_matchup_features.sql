-- 016_nfl_matchup_features.sql
-- Rolling team form features + matchup-level feature packs.

CREATE TABLE IF NOT EXISTS nfl_dp_team_rolling_features_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  games_in_window_3 int NOT NULL DEFAULT 0,
  games_in_window_5 int NOT NULL DEFAULT 0,
  off_epa_per_play_3g numeric,
  off_epa_per_play_5g numeric,
  def_epa_allowed_per_play_3g numeric,
  def_epa_allowed_per_play_5g numeric,
  pressure_rate_allowed_3g numeric,
  pressure_rate_allowed_5g numeric,
  pressure_rate_generated_3g numeric,
  pressure_rate_generated_5g numeric,
  pass_rate_3g numeric,
  pass_rate_5g numeric,
  early_down_pass_rate_3g numeric,
  early_down_pass_rate_5g numeric,
  red_zone_td_rate_3g numeric,
  red_zone_td_rate_5g numeric,
  success_rate_offense_3g numeric,
  success_rate_offense_5g numeric,
  success_rate_defense_allowed_3g numeric,
  success_rate_defense_allowed_5g numeric,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_rolling_team
  ON nfl_dp_team_rolling_features_weekly (team, season, week);

CREATE TABLE IF NOT EXISTS nfl_dp_matchup_features_weekly (
  season int NOT NULL,
  week int NOT NULL,
  game_id text NOT NULL,
  game_date date,
  home_team text NOT NULL,
  away_team text NOT NULL,
  home_off_epa_5g numeric,
  away_off_epa_5g numeric,
  home_def_epa_allowed_5g numeric,
  away_def_epa_allowed_5g numeric,
  home_pressure_allowed_5g numeric,
  away_pressure_allowed_5g numeric,
  home_pressure_generated_5g numeric,
  away_pressure_generated_5g numeric,
  home_pass_rate_5g numeric,
  away_pass_rate_5g numeric,
  home_early_down_pass_rate_5g numeric,
  away_early_down_pass_rate_5g numeric,
  home_red_zone_td_rate_5g numeric,
  away_red_zone_td_rate_5g numeric,
  home_success_offense_5g numeric,
  away_success_offense_5g numeric,
  home_success_defense_allowed_5g numeric,
  away_success_defense_allowed_5g numeric,
  diff_off_epa_5g numeric,
  diff_def_epa_allowed_5g numeric,
  diff_pressure_generated_5g numeric,
  diff_pressure_allowed_5g numeric,
  diff_red_zone_td_rate_5g numeric,
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, game_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_matchup_features_team_week
  ON nfl_dp_matchup_features_weekly (season, week, home_team, away_team);

CREATE OR REPLACE VIEW nfl_dp_team_rolling_features_latest AS
SELECT DISTINCT ON (t.team)
  t.*
FROM nfl_dp_team_rolling_features_weekly t
ORDER BY t.team, t.season DESC, t.week DESC;

CREATE OR REPLACE VIEW nfl_dp_matchup_features_latest AS
SELECT DISTINCT ON (m.game_id)
  m.*
FROM nfl_dp_matchup_features_weekly m
ORDER BY m.game_id, m.season DESC, m.week DESC;
