-- 055_nfl_dfs_foundation.sql
-- NFL DFS V1: site/slate/salary truth store.
-- Raw source payloads stay separate from normalized observations.
-- DK and FD salaries are distinct canonical observations — never interchangeable.

CREATE TABLE IF NOT EXISTS nfl_dfs_slate_raw (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site text NOT NULL CHECK (site IN ('DK', 'FD')),
  season int NOT NULL,
  week int NOT NULL,
  source text NOT NULL,
  source_version text NOT NULL,
  captured_at timestamptz NOT NULL,
  payload jsonb NOT NULL,
  payload_sha256 text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_dfs_slate_raw_lookup
  ON nfl_dfs_slate_raw (site, season, week, captured_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfl_dfs_slate_raw_payload
  ON nfl_dfs_slate_raw (site, season, week, payload_sha256);

CREATE TABLE IF NOT EXISTS nfl_dfs_slates (
  slate_uid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site text NOT NULL CHECK (site IN ('DK', 'FD')),
  season int NOT NULL,
  week int NOT NULL,
  slate_id text NOT NULL,
  slate_name text,
  contest_style text NOT NULL DEFAULT 'classic',
  game_count int,
  start_time timestamptz,
  source text NOT NULL,
  source_version text NOT NULL,
  captured_at timestamptz NOT NULL,
  is_current boolean NOT NULL DEFAULT TRUE,
  raw_id uuid REFERENCES nfl_dfs_slate_raw (id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (site, season, week, slate_id, source_version)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dfs_slates_current
  ON nfl_dfs_slates (site, season, week, is_current, captured_at DESC);

CREATE TABLE IF NOT EXISTS nfl_dfs_salary_observations (
  observation_uid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site text NOT NULL CHECK (site IN ('DK', 'FD')),
  season int NOT NULL,
  week int NOT NULL,
  slate_id text NOT NULL,
  source_player_id text NOT NULL,
  player_uid uuid,
  player_name text NOT NULL,
  team text NOT NULL,
  opponent text NOT NULL,
  position text NOT NULL,
  salary int NOT NULL CHECK (salary > 0),
  game_id text,
  game_label text,
  game_time timestamptz,
  source text NOT NULL,
  source_version text NOT NULL,
  captured_at timestamptz NOT NULL,
  is_current boolean NOT NULL DEFAULT TRUE,
  identity_status text NOT NULL DEFAULT 'unresolved'
    CHECK (identity_status IN ('resolved', 'unresolved', 'conflict', 'rejected')),
  identity_reason text,
  raw_id uuid REFERENCES nfl_dfs_slate_raw (id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfl_dfs_salary_obs_version
  ON nfl_dfs_salary_observations (site, slate_id, source_player_id, source_version);

CREATE INDEX IF NOT EXISTS idx_nfl_dfs_salary_obs_current
  ON nfl_dfs_salary_observations (site, season, week, slate_id, is_current);

CREATE INDEX IF NOT EXISTS idx_nfl_dfs_salary_obs_player
  ON nfl_dfs_salary_observations (player_uid, site, season, week)
  WHERE player_uid IS NOT NULL;

-- Ownership contract only. Rows may exist later; V1 publishes none.
CREATE TABLE IF NOT EXISTS nfl_dfs_ownership_projections (
  ownership_uid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site text NOT NULL CHECK (site IN ('DK', 'FD')),
  season int NOT NULL,
  week int NOT NULL,
  slate_id text NOT NULL,
  player_uid uuid NOT NULL,
  projected_own numeric,
  source text NOT NULL,
  source_version text NOT NULL,
  model_version text,
  captured_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'unavailable'
    CHECK (status IN ('unavailable', 'projected', 'rejected')),
  created_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (site, season, week, slate_id, player_uid, source_version)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dfs_ownership_lookup
  ON nfl_dfs_ownership_projections (site, season, week, slate_id, player_uid);
