-- 022_nfl_team_intel.sql
-- Derived standings and inferred depth charts for NFL Team Intel surfaces.

CREATE TABLE IF NOT EXISTS nfl_dp_standings_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  wins int NOT NULL DEFAULT 0,
  losses int NOT NULL DEFAULT 0,
  ties int NOT NULL DEFAULT 0,
  points_for int NOT NULL DEFAULT 0,
  points_against int NOT NULL DEFAULT 0,
  point_diff int NOT NULL DEFAULT 0,
  win_pct numeric,
  conference text,
  division text,
  conference_wins int,
  conference_losses int,
  conference_ties int,
  conference_pct numeric,
  division_wins int,
  division_losses int,
  division_ties int,
  division_pct numeric,
  source text NOT NULL DEFAULT 'nfl_dp_schedules_derived',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_standings_weekly_lookup
  ON nfl_dp_standings_weekly (season, week, team);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_standings_weekly_team
  ON nfl_dp_standings_weekly (team, season, week DESC);

CREATE TABLE IF NOT EXISTS nfl_dp_depth_chart_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  position text NOT NULL,
  depth_order int NOT NULL,
  depth_slot text NOT NULL,
  player_uid text,
  player_id text NOT NULL,
  player_name text,
  role_confidence numeric NOT NULL,
  inferred_source text NOT NULL DEFAULT 'v1_usage_roster_injury',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, position, depth_order),
  UNIQUE (season, week, team, position, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_depth_chart_weekly_lookup
  ON nfl_dp_depth_chart_weekly (season, week, team);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_depth_chart_weekly_player
  ON nfl_dp_depth_chart_weekly (player_id, season, week DESC);
