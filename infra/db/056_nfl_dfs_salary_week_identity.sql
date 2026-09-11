-- 056_nfl_dfs_salary_week_identity.sql
-- Salary observations must be unique per site/season/week/slate.
-- Reusing a slate_id such as "classic" in week 2 must not stale or overwrite week 1.

DROP INDEX IF EXISTS uq_nfl_dfs_salary_obs_version;

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfl_dfs_salary_obs_version
  ON nfl_dfs_salary_observations (site, season, week, slate_id, source_player_id, source_version);
