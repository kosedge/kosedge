-- 036_nfl_kicker_dst_fantasy.sql
-- Real Kicker (K) and Team Defense/Special Teams (DST) season-long fantasy
-- projections. See services/model-service/src/services/nfl_kicker_dst_projections.py
-- for the full methodology and docs/NFL_PROPS_FANTASY_FOUNDATION.md for the
-- rationale. Both new normalized tables below are built entirely from
-- ALREADY-INGESTED nflreadpy data -- `nfl_dp_player_game_stats.metrics`
-- (position = 'K') and `nfl_dp_raw_objects.payload` (object_type =
-- 'team_game_stats') -- no new external fetch is required, just a
-- normalization pass (see data_platform_nfl.kicking_defense_history).

-- Real per-kicker, per-game field goal (by nflverse's own 6 distance
-- buckets) and extra-point attempt/make counts -- the actual historical
-- signal `field_goals_by_bucket_mean` (see nfl_kicker_dst_projections.py) is
-- built from, with real per-kicker accuracy shrunk toward the league-average
-- bucket rate for low-sample kickers.
CREATE TABLE IF NOT EXISTS nfl_dp_kicker_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  game_id text,
  fg_att int NOT NULL DEFAULT 0,
  fg_made int NOT NULL DEFAULT 0,
  fg_att_0_19 int NOT NULL DEFAULT 0,
  fg_made_0_19 int NOT NULL DEFAULT 0,
  fg_att_20_29 int NOT NULL DEFAULT 0,
  fg_made_20_29 int NOT NULL DEFAULT 0,
  fg_att_30_39 int NOT NULL DEFAULT 0,
  fg_made_30_39 int NOT NULL DEFAULT 0,
  fg_att_40_49 int NOT NULL DEFAULT 0,
  fg_made_40_49 int NOT NULL DEFAULT 0,
  fg_att_50_59 int NOT NULL DEFAULT 0,
  fg_made_50_59 int NOT NULL DEFAULT 0,
  fg_att_60_plus int NOT NULL DEFAULT 0,
  fg_made_60_plus int NOT NULL DEFAULT 0,
  pat_att int NOT NULL DEFAULT 0,
  pat_made int NOT NULL DEFAULT 0,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_kicker_weekly_player
  ON nfl_dp_kicker_weekly (player_id, season, week);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_kicker_weekly_team
  ON nfl_dp_kicker_weekly (team, season, week);

-- Real per-team, per-game defense/special-teams counting stats (sacks,
-- interceptions, fumble recoveries, defensive+special-teams touchdowns,
-- safeties) -- `points_allowed` is carried alongside for convenience but is
-- the SAME real value already normalized onto `nfl_dp_team_game_stats.points_against`,
-- not a second independent number.
CREATE TABLE IF NOT EXISTS nfl_dp_team_defense_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  opponent text,
  game_id text,
  points_allowed numeric,
  sacks numeric NOT NULL DEFAULT 0,
  interceptions numeric NOT NULL DEFAULT 0,
  fumble_recoveries numeric NOT NULL DEFAULT 0,
  defensive_tds numeric NOT NULL DEFAULT 0,
  special_teams_tds numeric NOT NULL DEFAULT 0,
  safeties numeric NOT NULL DEFAULT 0,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_defense_weekly_team
  ON nfl_dp_team_defense_weekly (team, season, week);

-- Extend the season-long draft board with K/DST-specific projected counting
-- stats -- the existing pass/rush/receiving columns stay NULL for K/DST rows
-- (those positions don't generate that offensive counting-stat shape), same
-- convention as `nfl_award_projections` leaving position-inapplicable columns
-- NULL rather than 0 (0 would misleadingly imply "projected to record zero",
-- vs. NULL's honest "not applicable to this position").
ALTER TABLE nfl_fantasy_season_draft_rankings
  ADD COLUMN IF NOT EXISTS field_goals_made_total numeric,
  ADD COLUMN IF NOT EXISTS field_goals_attempted_total numeric,
  ADD COLUMN IF NOT EXISTS extra_points_made_total numeric,
  ADD COLUMN IF NOT EXISTS points_allowed_total numeric,
  ADD COLUMN IF NOT EXISTS sacks_total numeric,
  ADD COLUMN IF NOT EXISTS def_interceptions_total numeric,
  ADD COLUMN IF NOT EXISTS fumble_recoveries_total numeric,
  ADD COLUMN IF NOT EXISTS defensive_tds_total numeric,
  ADD COLUMN IF NOT EXISTS safeties_total numeric;
