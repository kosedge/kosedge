-- 035_nfl_situational_tendency_profiles.sql
-- Real, honest situational/tendency analytics computed from normalized
-- nflverse play-by-play (nfl_dp_play_by_play, extended by
-- 034_nfl_pbp_tendency_columns.sql). See
-- services/data-platform-nfl/src/data_platform_nfl/tendency_profiles.py for
-- the computation and docs/NFL_TENDENCY_ANALYTICS.md for scope/provenance.
--
-- Explicitly NOT covered anywhere in this layer: defensive coverage-scheme
-- labels (Cover 2/Cover 3/man/zone), pass-rusher counts, personnel
-- groupings, or box counts -- none of those exist in free nflverse/
-- nflreadpy PBP. Every column here is a real, situational, tendency-style
-- signal (down/distance, score state, field position, direction, pace,
-- pass-rate-over-expected vs. nflfastR's own `xpass` model, pressure proxy
-- via real sack/qb_hit) computed directly from real historical plays.

-- One row per (season, team, perspective, situation_type, situation_bucket).
-- perspective = 'offense' groups by posteam (this team's own tendencies);
-- perspective = 'defense' groups by defteam (tendencies this team's
-- defense faces/allows) -- the "flip side" needed for real matchup
-- breakdowns (Team A offense tendency in situation X vs. Team B defense
-- tendency allowed in that same situation X).
CREATE TABLE IF NOT EXISTS nfl_dp_team_situational_tendencies (
  season int NOT NULL,
  team text NOT NULL,
  perspective text NOT NULL, -- offense|defense
  situation_type text NOT NULL, -- down_distance|score_state|field_position
  situation_bucket text NOT NULL,
  plays int NOT NULL DEFAULT 0,
  pass_plays int NOT NULL DEFAULT 0,
  rush_plays int NOT NULL DEFAULT 0,
  pass_rate numeric,
  dropback_plays int NOT NULL DEFAULT 0,
  dropback_rate numeric,
  avg_xpass numeric,
  pass_rate_over_expected numeric, -- dropback_rate - avg_xpass (real PROE vs. nflfastR's own dropback-probability model)
  shotgun_plays int NOT NULL DEFAULT 0,
  shotgun_rate numeric,
  no_huddle_plays int NOT NULL DEFAULT 0,
  no_huddle_rate numeric,
  epa_per_play numeric,
  success_rate numeric,
  explosive_play_rate numeric,
  sack_rate numeric, -- pressure proxy (offense: sacks taken/dropback; defense: sacks generated/dropback faced)
  source text NOT NULL DEFAULT 'nflverse',
  computed_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, team, perspective, situation_type, situation_bucket)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_team_situational_tendencies_lookup
  ON nfl_dp_team_situational_tendencies (season, team, perspective);

-- One row per (season, team, perspective) -- pass direction (left/middle/
-- right) and run direction/gap (location + gap) tendency. team = 'LEAGUE'
-- holds the league-wide average row for context (per the task's ask for
-- "per team and league-wide for context").
CREATE TABLE IF NOT EXISTS nfl_dp_team_direction_tendencies (
  season int NOT NULL,
  team text NOT NULL,
  perspective text NOT NULL, -- offense|defense
  pass_plays_with_location int NOT NULL DEFAULT 0,
  pass_left_rate numeric,
  pass_middle_rate numeric,
  pass_right_rate numeric,
  run_plays_with_location int NOT NULL DEFAULT 0,
  run_left_rate numeric,
  run_middle_rate numeric,
  run_right_rate numeric,
  run_plays_with_gap int NOT NULL DEFAULT 0,
  run_end_rate numeric,
  run_guard_rate numeric,
  run_tackle_rate numeric,
  source text NOT NULL DEFAULT 'nflverse',
  computed_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, team, perspective)
);

-- QB situational efficiency splits. situation_type in
-- ('overall','down_type','pressure','score_state','field_position').
-- 'pressure' buckets ('pressure'/'clean_pocket') use real sack/qb_hit as
-- the honest pressure proxy -- we do not have a real pass-rusher-count or
-- blitz column.
CREATE TABLE IF NOT EXISTS nfl_dp_qb_situational_splits (
  season int NOT NULL,
  player_id text NOT NULL,
  player_name text,
  team text,
  situation_type text NOT NULL,
  situation_bucket text NOT NULL,
  dropbacks int NOT NULL DEFAULT 0,
  pass_attempts int NOT NULL DEFAULT 0,
  completions int NOT NULL DEFAULT 0,
  completion_rate numeric,
  pass_yards numeric,
  yards_per_attempt numeric,
  epa_per_play numeric,
  success_rate numeric,
  avg_cp numeric,
  cpoe numeric, -- (completion_rate - avg_cp) * 100, percentage points
  sacks int NOT NULL DEFAULT 0,
  sack_rate numeric,
  interceptions int NOT NULL DEFAULT 0,
  interception_rate numeric,
  passing_tds int NOT NULL DEFAULT 0,
  td_rate numeric,
  source text NOT NULL DEFAULT 'nflverse',
  computed_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, player_id, situation_type, situation_bucket)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_qb_situational_splits_lookup
  ON nfl_dp_qb_situational_splits (season, player_id);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_qb_situational_splits_team
  ON nfl_dp_qb_situational_splits (season, team);
