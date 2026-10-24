-- 057_nfl_dp_injuries_report_time.sql
-- Listing as-of (C-4 / §7.1.3). Distinct from ingest updated_at.
-- NULL means missing; never backfilled with NOW().

ALTER TABLE nfl_dp_injuries
  ADD COLUMN IF NOT EXISTS report_time timestamptz;

COMMENT ON COLUMN nfl_dp_injuries.report_time IS
  'Source listing timestamp (nflverse date_modified/date_reported). listing_as_of alias. NULL = missing, fail closed.';

CREATE INDEX IF NOT EXISTS idx_nfl_dp_injuries_report_time
  ON nfl_dp_injuries (season, week, team, report_time);
