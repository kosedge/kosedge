-- 030_nfl_usage_weekly_source_tracking.sql
-- nfl_dp_player_usage_weekly had no `source` column, so there was no way
-- to distinguish real play-by-play-derived rows from synthetic preseason
-- priors once written -- which is exactly how an ad-hoc, uncommitted
-- carry-forward script was able to silently seed flat placeholder rows for
-- an entire future season with nothing marking them as such.
--
-- Going forward every writer must tag its rows:
--   'pbp_aggregation'      - real, from materialize_usage_features_from_pbp
--   'preseason_hydrate_v1'  - full prior-season average (see preseason_hydration.py)
--   'rookie_baseline_v1'    - historical draft-tier baseline (see rookie_baselines.py)
--
-- This is the safety guard that lets preseason_hydration.py be re-run any
-- time without ever clobbering real in-season data: it only overwrites rows
-- whose source is one of the two synthetic tags above.

ALTER TABLE nfl_dp_player_usage_weekly
  ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'pbp_aggregation';

CREATE INDEX IF NOT EXISTS idx_nfl_dp_player_usage_weekly_source
  ON nfl_dp_player_usage_weekly (season, week, source);
