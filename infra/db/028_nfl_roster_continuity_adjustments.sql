-- 028_nfl_roster_continuity_adjustments.sql
-- Explicit, human-inspectable record of known offseason roster moves
-- (free agency/trade departures, retirements, notable signings, and
-- long-term injuries known before the season starts) that should adjust
-- a team's preseason strength prior beyond what the season-average-EPA +
-- market-futures-odds blend (see scripts/nfl/fix_2026_preseason_priors.py)
-- captures on its own.
--
-- Rows here are converted into the SAME offense_multiplier/defense_multiplier
-- shape produced by the in-season injury nowcast (see
-- services/model-service/src/services/nfl_injury_nowcast.py's
-- _aggregate_team_nowcast) via
-- services/model-service/src/services/nfl_roster_continuity.py, and merged
-- into fetch_nfl_injury_nowcast()'s output so they flow through the
-- existing NflGameInputs multiplier path used by the simulator -- no
-- separate adjustment mechanism, no mutation of raw EPA inputs.
--
-- Populate via scripts/nfl/add_roster_adjustment.py (CLI) or direct insert.

CREATE TABLE IF NOT EXISTS nfl_roster_continuity_adjustments (
  id bigserial PRIMARY KEY,
  season integer NOT NULL,
  team text NOT NULL,
  player_name text,
  position_group text NOT NULL,
  impact_score numeric NOT NULL CHECK (impact_score >= -1 AND impact_score <= 1),
  reason text NOT NULL CHECK (reason IN ('departure', 'trade', 'retirement', 'injury', 'signing', 'other')),
  source text NOT NULL DEFAULT 'manual',
  notes text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_nfl_roster_continuity_adjustments_season_team
  ON nfl_roster_continuity_adjustments (season, team)
  WHERE active;
