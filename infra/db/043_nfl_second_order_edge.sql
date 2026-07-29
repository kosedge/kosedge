-- 043_nfl_second_order_edge.sql
-- Second-order edge foundation: PBP personnel/win-prob columns, external
-- source cache, personnel efficiency, substitution elasticity, coach
-- aggression weekly tables, and matchup-pack extensions.
--
-- Leakage rule (all weekly feature tables): row for week W is as-of end of W.
-- Pre-game joins for a game in week G MUST use week = G-1 (strict lag).

-- ---------------------------------------------------------------------------
-- Normalized PBP extensions (backfill via normalize_pbp_from_raw --replace)
-- ---------------------------------------------------------------------------
ALTER TABLE nfl_dp_play_by_play
  ADD COLUMN IF NOT EXISTS offense_personnel text,
  ADD COLUMN IF NOT EXISTS defense_personnel text,
  ADD COLUMN IF NOT EXISTS wp numeric,
  ADD COLUMN IF NOT EXISTS vegas_wp numeric,
  ADD COLUMN IF NOT EXISTS fixed_drive int,
  ADD COLUMN IF NOT EXISTS series int,
  ADD COLUMN IF NOT EXISTS qtr int,
  ADD COLUMN IF NOT EXISTS half_seconds_remaining numeric,
  ADD COLUMN IF NOT EXISTS game_seconds_remaining numeric;

-- ---------------------------------------------------------------------------
-- Generic external-source response cache (VC / OTC / Spotrac / PFF)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nfl_dp_external_cache (
  source text NOT NULL,
  cache_key text NOT NULL,
  season int,
  week int,
  object_type text NOT NULL DEFAULT 'response',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  http_status int,
  fetched_at timestamptz NOT NULL DEFAULT NOW(),
  expires_at timestamptz,
  notes text,
  PRIMARY KEY (source, cache_key)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_external_cache_expires
  ON nfl_dp_external_cache (expires_at);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_external_cache_source_fetched
  ON nfl_dp_external_cache (source, fetched_at DESC);

-- Visual Crossing weather day cache (respect ~1000/day free tier).
CREATE TABLE IF NOT EXISTS nfl_dp_weather_forecast_cache (
  location_key text NOT NULL,
  forecast_date date NOT NULL,
  provider text NOT NULL DEFAULT 'visual_crossing',
  lat numeric,
  lon numeric,
  temp_f numeric,
  wind_mph numeric,
  precip_mm numeric,
  humidity numeric,
  conditions text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  fetched_at timestamptz NOT NULL DEFAULT NOW(),
  expires_at timestamptz,
  PRIMARY KEY (location_key, forecast_date, provider)
);

-- ---------------------------------------------------------------------------
-- nflverse participation weekly (snap/route participation aggregates)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nfl_dp_participation_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_name text,
  position text,
  offense_snaps int NOT NULL DEFAULT 0,
  defense_snaps int NOT NULL DEFAULT 0,
  st_snaps int NOT NULL DEFAULT 0,
  offense_pct numeric,
  defense_pct numeric,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nflverse_participation',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_participation_weekly_team
  ON nfl_dp_participation_weekly (team, season, week);

-- ---------------------------------------------------------------------------
-- Personnel efficiency (package-level EPA / success; week-lagged)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nfl_dp_personnel_efficiency_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  plays int NOT NULL DEFAULT 0,
  personnel_11_rate numeric,
  personnel_12_rate numeric,
  personnel_21_rate numeric,
  personnel_13_rate numeric,
  personnel_other_rate numeric,
  epa_11 numeric,
  epa_12 numeric,
  epa_21 numeric,
  epa_weighted numeric,
  success_weighted numeric,
  personnel_edge numeric,
  personnel_edge_5g numeric,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nflverse_pbp',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_personnel_eff_team
  ON nfl_dp_personnel_efficiency_weekly (team, season, week);

CREATE OR REPLACE VIEW nfl_dp_personnel_efficiency_latest AS
SELECT DISTINCT ON (t.team)
  t.*
FROM nfl_dp_personnel_efficiency_weekly t
ORDER BY t.team, t.season DESC, t.week DESC;

-- ---------------------------------------------------------------------------
-- Substitution elasticity (usage response to snap-share shocks)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nfl_dp_substitution_elasticity_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  position_group text NOT NULL,
  sample_players int NOT NULL DEFAULT 0,
  mean_snap_pct numeric,
  snap_pct_volatility numeric,
  epa_per_snap_pct numeric,
  elasticity numeric,
  elasticity_5g numeric,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nflverse_snaps_pbp',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, position_group)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_sub_elasticity_team
  ON nfl_dp_substitution_elasticity_weekly (team, season, week);

-- ---------------------------------------------------------------------------
-- Coach aggression latents (team-season leadership proxy via play-calling)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nfl_coach_aggression_weekly (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  plays int NOT NULL DEFAULT 0,
  fourth_down_attempts int NOT NULL DEFAULT 0,
  fourth_down_go_rate numeric,
  fourth_down_go_residual numeric,
  early_down_proe numeric,
  no_huddle_rate numeric,
  trailing_pass_rate numeric,
  leading_pass_rate numeric,
  aggression_latent numeric,
  aggression_latent_5g numeric,
  pace_latent numeric,
  pace_latent_5g numeric,
  as_of_week int NOT NULL,
  source text NOT NULL DEFAULT 'nflverse_pbp',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team)
);

CREATE INDEX IF NOT EXISTS idx_nfl_coach_aggression_team
  ON nfl_coach_aggression_weekly (team, season, week);

CREATE OR REPLACE VIEW nfl_coach_aggression_latest AS
SELECT DISTINCT ON (t.team)
  t.*
FROM nfl_coach_aggression_weekly t
ORDER BY t.team, t.season DESC, t.week DESC;

-- ---------------------------------------------------------------------------
-- Matchup pack extensions (nullable until materializers fill)
-- ---------------------------------------------------------------------------
ALTER TABLE nfl_dp_matchup_features_weekly
  ADD COLUMN IF NOT EXISTS home_personnel_edge_5g numeric,
  ADD COLUMN IF NOT EXISTS away_personnel_edge_5g numeric,
  ADD COLUMN IF NOT EXISTS diff_personnel_edge_5g numeric,
  ADD COLUMN IF NOT EXISTS home_sub_elasticity_5g numeric,
  ADD COLUMN IF NOT EXISTS away_sub_elasticity_5g numeric,
  ADD COLUMN IF NOT EXISTS home_coach_aggression_5g numeric,
  ADD COLUMN IF NOT EXISTS away_coach_aggression_5g numeric,
  ADD COLUMN IF NOT EXISTS diff_coach_aggression_5g numeric,
  ADD COLUMN IF NOT EXISTS home_coach_pace_5g numeric,
  ADD COLUMN IF NOT EXISTS away_coach_pace_5g numeric,
  ADD COLUMN IF NOT EXISTS second_order_as_of_week int;
