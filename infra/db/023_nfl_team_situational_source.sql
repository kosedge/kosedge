-- 023_nfl_team_situational_source.sql
-- Track source priority for weekly team situational stats.

ALTER TABLE nfl_dp_team_situational_weekly
  ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'nflverse';

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_situational_weekly_source
  ON nfl_dp_team_situational_weekly (season, week, source);
