-- 029_nfl_rookie_draft_capital.sql
-- Adds real draft-capital identity fields to the roster table (sourced
-- directly from nflreadpy's load_rosters(), which already carries
-- entry_year/rookie_year/draft_number -- previously fetched into memory
-- during ingest_nflverse_snapshot() but discarded before the INSERT).
--
-- This is the join key that lets a player be classified as a rookie
-- (rookie_year == season, no prior-season usage row) vs a veteran, and
-- lets rookies be bucketed by draft capital for the historical usage
-- baseline in nfl_dp_rookie_usage_baselines below.
--
-- See services/data-platform-nfl/src/data_platform_nfl/rookie_baselines.py
-- and preseason_hydration.py for how these are consumed.

ALTER TABLE nfl_dp_rosters
  ADD COLUMN IF NOT EXISTS entry_year integer,
  ADD COLUMN IF NOT EXISTS rookie_year integer,
  ADD COLUMN IF NOT EXISTS draft_number integer;

CREATE INDEX IF NOT EXISTS idx_nfl_dp_rosters_rookie_year
  ON nfl_dp_rosters (rookie_year, position)
  WHERE rookie_year IS NOT NULL;

-- Historical rookie-year usage baselines, computed from every real rookie
-- season 2013-present (rookie_year = season, joined to their actual
-- nfl_dp_player_usage_weekly production that year). Bucketed by position +
-- draft-capital tier since draft capital is the single strongest predictor
-- of Year-1 opportunity. Refreshed on demand via
-- rookie_baselines.compute_rookie_usage_baselines(); never hand-edited.
CREATE TABLE IF NOT EXISTS nfl_dp_rookie_usage_baselines (
  position text NOT NULL,
  draft_tier text NOT NULL,
  sample_players integer NOT NULL,
  sample_player_weeks integer NOT NULL,
  avg_games_played numeric,
  avg_involvement_plays_per_game numeric,
  avg_targets_per_game numeric,
  avg_receptions_per_game numeric,
  avg_receiving_yards_per_game numeric,
  avg_rush_attempts_per_game numeric,
  avg_rush_yards_per_game numeric,
  avg_red_zone_targets_per_game numeric,
  avg_red_zone_carries_per_game numeric,
  avg_qb_dropbacks_per_game numeric,
  avg_success_rate numeric,
  computed_through_season integer NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (position, draft_tier)
);
