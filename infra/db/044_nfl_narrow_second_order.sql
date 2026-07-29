-- 044_nfl_narrow_second_order.sql
-- Narrow second-order path: injury info-velocity support index + optional
-- weekly velocity cache for leakage-safe historical joins (week W uses W-1).
--
-- Does NOT add OTC/PFF/Spotrac tables. VC weather cache lives in 043.

CREATE INDEX IF NOT EXISTS idx_nfl_dp_injuries_season_week_team
  ON nfl_dp_injuries (season, week, team);

CREATE TABLE IF NOT EXISTS nfl_dp_injury_info_velocity_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  velocity_score numeric,
  upgrade_count int NOT NULL DEFAULT 0,
  downgrade_count int NOT NULL DEFAULT 0,
  change_count int NOT NULL DEFAULT 0,
  hours_since_change numeric,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nfl_dp_injuries_wow',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_injury_info_velocity_team
  ON nfl_dp_injury_info_velocity_weekly (team, season, week);

-- Optional matchup pack pass-through (nullable until materializer fills).
ALTER TABLE nfl_dp_matchup_features_weekly
  ADD COLUMN IF NOT EXISTS home_info_velocity_score numeric,
  ADD COLUMN IF NOT EXISTS away_info_velocity_score numeric,
  ADD COLUMN IF NOT EXISTS diff_info_velocity_score numeric,
  ADD COLUMN IF NOT EXISTS home_hours_since_injury_change numeric,
  ADD COLUMN IF NOT EXISTS away_hours_since_injury_change numeric;
