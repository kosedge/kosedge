-- 048_mlb_model_handicap_lines.sql
-- Persist pure-sim model_* separately from KEI handicap (published fair_fg_*).
-- fair_fg_* remains the handicap alias for one release; model_* is snapshotted
-- at first write and preserved across nowcast repricing.

ALTER TABLE mlb_market_projections
  ADD COLUMN IF NOT EXISTS model_fg_home_win_prob numeric,
  ADD COLUMN IF NOT EXISTS model_fg_total_mean numeric,
  ADD COLUMN IF NOT EXISTS model_fair_fg_home_ml int,
  ADD COLUMN IF NOT EXISTS model_fair_fg_total numeric,
  ADD COLUMN IF NOT EXISTS model_fair_fg_spread_home numeric,
  ADD COLUMN IF NOT EXISTS handicap_fg_home_win_prob numeric,
  ADD COLUMN IF NOT EXISTS handicap_fg_total_mean numeric,
  ADD COLUMN IF NOT EXISTS handicap_fair_fg_home_ml int,
  ADD COLUMN IF NOT EXISTS handicap_fair_fg_total numeric,
  ADD COLUMN IF NOT EXISTS handicap_fair_fg_spread_home numeric;

COMMENT ON COLUMN mlb_market_projections.model_fair_fg_home_ml IS
  'Pure sim / research fair home ML (American); snapshotted at first write';
COMMENT ON COLUMN mlb_market_projections.handicap_fair_fg_home_ml IS
  'KEI product handicap home ML; mirrors fair_fg_home_ml during migration';
COMMENT ON COLUMN mlb_market_projections.fair_fg_home_ml IS
  'Alias of handicap_fair_fg_home_ml (KEI product line) for one release';
