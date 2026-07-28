-- 041_nfl_kav_efficiency.sql
-- KAV = Kos Edge Adjusted Value: owned opponent-adjusted efficiency
-- (DVOA-style conceptually; NOT Football Outsiders / FTN DVOA).

CREATE TABLE IF NOT EXISTS nfl_dp_team_kav_game (
  season int NOT NULL,
  week int NOT NULL,
  game_id text NOT NULL,
  team text NOT NULL,
  opponent text NOT NULL,
  is_home boolean,
  off_plays int NOT NULL DEFAULT 0,
  def_plays int NOT NULL DEFAULT 0,
  raw_off_epa_per_play numeric,
  raw_def_epa_allowed_per_play numeric,
  raw_off_success_rate numeric,
  raw_def_success_allowed_rate numeric,
  raw_off_explosive_rate numeric,
  raw_def_explosive_allowed_rate numeric,
  kav_off_epa_per_play numeric,
  kav_def_epa_allowed_per_play numeric,
  kav_offense numeric,
  kav_defense numeric,
  kav_net numeric,
  iterations int NOT NULL DEFAULT 0,
  source text NOT NULL DEFAULT 'nflverse_pbp',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, game_id, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_kav_game_team
  ON nfl_dp_team_kav_game (team, season, week);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_kav_game_opp
  ON nfl_dp_team_kav_game (opponent, season, week);

-- Cumulative / as-of ratings through end of `week` (includes that week's games).
-- For pre-game features in week W, join week = W-1 (strict lag, no leakage).
CREATE TABLE IF NOT EXISTS nfl_dp_team_kav_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  games_played int NOT NULL DEFAULT 0,
  off_plays int NOT NULL DEFAULT 0,
  def_plays int NOT NULL DEFAULT 0,
  raw_off_epa_per_play numeric,
  raw_def_epa_allowed_per_play numeric,
  kav_off_epa_per_play numeric,
  kav_def_epa_allowed_per_play numeric,
  kav_offense numeric,
  kav_defense numeric,
  kav_net numeric,
  kav_offense_ytd numeric,
  kav_defense_ytd numeric,
  kav_net_ytd numeric,
  kav_offense_5g numeric,
  kav_defense_5g numeric,
  kav_net_5g numeric,
  iterations int NOT NULL DEFAULT 0,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nflverse_pbp',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_kav_weekly_team
  ON nfl_dp_team_kav_weekly (team, season, week);

CREATE OR REPLACE VIEW nfl_dp_team_kav_latest AS
SELECT DISTINCT ON (t.team)
  t.*
FROM nfl_dp_team_kav_weekly t
ORDER BY t.team, t.season DESC, t.week DESC;

-- Matchup pack extensions for KAV (nullable until materializer fills).
ALTER TABLE nfl_dp_matchup_features_weekly
  ADD COLUMN IF NOT EXISTS home_kav_offense_5g numeric,
  ADD COLUMN IF NOT EXISTS away_kav_offense_5g numeric,
  ADD COLUMN IF NOT EXISTS home_kav_defense_5g numeric,
  ADD COLUMN IF NOT EXISTS away_kav_defense_5g numeric,
  ADD COLUMN IF NOT EXISTS home_kav_net_5g numeric,
  ADD COLUMN IF NOT EXISTS away_kav_net_5g numeric,
  ADD COLUMN IF NOT EXISTS home_kav_offense_ytd numeric,
  ADD COLUMN IF NOT EXISTS away_kav_offense_ytd numeric,
  ADD COLUMN IF NOT EXISTS home_kav_defense_ytd numeric,
  ADD COLUMN IF NOT EXISTS away_kav_defense_ytd numeric,
  ADD COLUMN IF NOT EXISTS home_kav_net_ytd numeric,
  ADD COLUMN IF NOT EXISTS away_kav_net_ytd numeric,
  ADD COLUMN IF NOT EXISTS diff_kav_offense_5g numeric,
  ADD COLUMN IF NOT EXISTS diff_kav_defense_5g numeric,
  ADD COLUMN IF NOT EXISTS diff_kav_net_5g numeric,
  ADD COLUMN IF NOT EXISTS kav_as_of_week int;
