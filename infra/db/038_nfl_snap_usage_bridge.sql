-- 038_nfl_snap_usage_bridge.sql
-- Bridge nflverse snap counts (PFR ids) onto GSIS usage/feature rows, and
-- persist offense snap fields on projection features for RB/WR usage tracking.

ALTER TABLE nfl_dp_snap_counts_weekly
  ADD COLUMN IF NOT EXISTS gsis_player_id text;

CREATE INDEX IF NOT EXISTS idx_nfl_dp_snap_counts_weekly_gsis
  ON nfl_dp_snap_counts_weekly (season, week, team, gsis_player_id)
  WHERE gsis_player_id IS NOT NULL;

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS offense_snaps numeric;

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS offense_snap_pct numeric;

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS snap_source text;
