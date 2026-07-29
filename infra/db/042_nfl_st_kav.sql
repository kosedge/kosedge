-- 042_nfl_st_kav.sql
-- Special-teams KAV companion: owned PBP EPA on FG/XP/punt/kickoff,
-- week-lagged rolling features for supervised + matchup packs.

CREATE TABLE IF NOT EXISTS nfl_dp_team_st_kav_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  games_played int NOT NULL DEFAULT 0,
  st_plays int NOT NULL DEFAULT 0,
  raw_st_epa_per_play numeric,
  st_kav_net numeric,
  st_kav_net_5g numeric,
  st_kav_net_ytd numeric,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nflverse_pbp_st',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_st_kav_weekly_team
  ON nfl_dp_team_st_kav_weekly (team, season, week);

ALTER TABLE nfl_dp_matchup_features_weekly
  ADD COLUMN IF NOT EXISTS home_st_kav_net_5g numeric,
  ADD COLUMN IF NOT EXISTS away_st_kav_net_5g numeric,
  ADD COLUMN IF NOT EXISTS diff_st_kav_net_5g numeric;
