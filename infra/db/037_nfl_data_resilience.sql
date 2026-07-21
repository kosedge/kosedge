-- 037_nfl_data_resilience.sql
-- Enterprise DR backups, freshness SLOs, ops alerts, and model-critical snap/depth ownership.

ALTER TABLE nfl_data_ownership_backups
  ADD COLUMN IF NOT EXISTS backup_type text NOT NULL DEFAULT 'manifest',
  ADD COLUMN IF NOT EXISTS dump_path text,
  ADD COLUMN IF NOT EXISTS dump_checksum text,
  ADD COLUMN IF NOT EXISTS dump_bytes bigint,
  ADD COLUMN IF NOT EXISTS remote_uri text,
  ADD COLUMN IF NOT EXISTS verify_status text,
  ADD COLUMN IF NOT EXISTS verify_details jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_nfl_data_ownership_backups_type_created
  ON nfl_data_ownership_backups (backup_type, created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_ops_alert_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_type text NOT NULL,
  severity text NOT NULL,
  source text NOT NULL DEFAULT 'nfl',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  webhook_delivered boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_ops_alert_events_created
  ON nfl_ops_alert_events (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_ops_alert_events_type
  ON nfl_ops_alert_events (alert_type, created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_data_freshness_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  status text NOT NULL,
  season int,
  week int,
  checks jsonb NOT NULL DEFAULT '{}'::jsonb,
  blockers jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_matrix jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_data_freshness_snapshots_created
  ON nfl_data_freshness_snapshots (created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_dp_snap_counts_weekly (
  season int NOT NULL,
  week int NOT NULL,
  game_id text,
  player_id text NOT NULL,
  player_name text,
  team text NOT NULL,
  position text,
  offense_snaps numeric,
  offense_pct numeric,
  defense_snaps numeric,
  defense_pct numeric,
  st_snaps numeric,
  st_pct numeric,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_snap_counts_weekly_lookup
  ON nfl_dp_snap_counts_weekly (season, week, team);

CREATE TABLE IF NOT EXISTS nfl_dp_official_depth_charts (
  season int NOT NULL,
  week int NOT NULL,
  team text NOT NULL,
  position text NOT NULL,
  depth_team int NOT NULL DEFAULT 1,
  player_id text NOT NULL,
  player_name text,
  source text NOT NULL DEFAULT 'nflverse',
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, week, team, position, depth_team, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_dp_official_depth_charts_lookup
  ON nfl_dp_official_depth_charts (season, week, team, position);
