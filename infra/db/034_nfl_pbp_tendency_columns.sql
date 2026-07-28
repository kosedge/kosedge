-- 034_nfl_pbp_tendency_columns.sql
-- Carry forward real, already-ingested nflverse PBP columns that the
-- original normalization (013_nfl_pbp_normalized.sql) narrowed away, but
-- which are required for honest situational-tendency analytics:
--
--   shotgun, no_huddle, qb_dropback  - real pre-snap/play-call booleans
--   pass_location, run_location, run_gap - real direction/gap labels
--   xpass  - nflfastR's real, model-derived P(dropback | situation); the
--            correct baseline for a real "pass rate over expected" (PROE)
--            tendency signal
--   cp, xyac_epa - real completion-probability / expected-YAC-EPA model
--                  outputs, used for CPOE-style QB situational splits
--
-- None of these are coverage-scheme labels (no Cover 2/3, man/zone, or any
-- defender-alignment field exists anywhere in free nflverse/nflreadpy PBP --
-- confirmed directly against the raw ingested payloads in
-- nfl_dp_raw_objects before writing this migration). They are legitimate
-- nflfastR-computed situational/tendency signals only.

ALTER TABLE nfl_dp_play_by_play
  ADD COLUMN IF NOT EXISTS shotgun boolean,
  ADD COLUMN IF NOT EXISTS no_huddle boolean,
  ADD COLUMN IF NOT EXISTS qb_dropback boolean,
  ADD COLUMN IF NOT EXISTS pass_location text,
  ADD COLUMN IF NOT EXISTS run_location text,
  ADD COLUMN IF NOT EXISTS run_gap text,
  ADD COLUMN IF NOT EXISTS xpass numeric,
  ADD COLUMN IF NOT EXISTS cp numeric,
  ADD COLUMN IF NOT EXISTS xyac_epa numeric;

-- Re-normalization (normalize_pbp_from_raw with --replace-normalized) is
-- required after this migration to actually backfill these columns for
-- already-normalized seasons -- ALTER TABLE alone only adds the columns as
-- NULL for existing rows. The raw source data in nfl_dp_raw_objects already
-- has these fields for every previously-ingested season, so no new
-- nflverse/nflreadpy fetch is needed, only a re-run of the normalization
-- step.
