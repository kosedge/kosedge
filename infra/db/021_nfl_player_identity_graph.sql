-- 021_nfl_player_identity_graph.sql
-- Canonical NFL player identity graph with resolver auditability and weekly SLA snapshots.

CREATE TABLE IF NOT EXISTS nfl_player_identities (
  player_uid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL,
  normalized_name text NOT NULL,
  primary_team text,
  primary_position text,
  active_from_season int,
  active_to_season int,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_identities_normalized_name
  ON nfl_player_identities (normalized_name);

CREATE INDEX IF NOT EXISTS idx_nfl_player_identities_team_position
  ON nfl_player_identities (primary_team, primary_position);

CREATE TABLE IF NOT EXISTS nfl_player_source_id_map (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_system text NOT NULL,
  external_id text NOT NULL,
  player_uid uuid NOT NULL REFERENCES nfl_player_identities(player_uid) ON DELETE CASCADE,
  confidence numeric NOT NULL DEFAULT 1.0,
  trusted_link boolean NOT NULL DEFAULT false,
  first_seen_at timestamptz NOT NULL DEFAULT NOW(),
  last_seen_at timestamptz NOT NULL DEFAULT NOW(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (source_system, external_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_source_id_map_player_uid
  ON nfl_player_source_id_map (player_uid);

CREATE INDEX IF NOT EXISTS idx_nfl_player_source_id_map_last_seen
  ON nfl_player_source_id_map (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS nfl_player_aliases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  player_uid uuid NOT NULL REFERENCES nfl_player_identities(player_uid) ON DELETE CASCADE,
  source_system text,
  alias text NOT NULL,
  normalized_alias text NOT NULL,
  team text NOT NULL DEFAULT '',
  position text NOT NULL DEFAULT '',
  season int NOT NULL DEFAULT -1,
  week int NOT NULL DEFAULT -1,
  context jsonb NOT NULL DEFAULT '{}'::jsonb,
  first_seen_at timestamptz NOT NULL DEFAULT NOW(),
  last_seen_at timestamptz NOT NULL DEFAULT NOW(),
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (player_uid, normalized_alias, team, position, season, week)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_aliases_lookup
  ON nfl_player_aliases (normalized_alias, team, position);

CREATE INDEX IF NOT EXISTS idx_nfl_player_aliases_season_week
  ON nfl_player_aliases (season, week);

CREATE TABLE IF NOT EXISTS nfl_player_mapping_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  observed_source text NOT NULL,
  observed_external_id text,
  observed_player_name text,
  normalized_name text NOT NULL,
  observed_team text,
  observed_position text,
  observed_season int,
  observed_week int,
  resolver_version text NOT NULL,
  rule_used text NOT NULL,
  confidence numeric NOT NULL DEFAULT 0.0,
  status text NOT NULL, -- mapped|unresolved|conflict|rejected|manual_approved
  player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL,
  candidate_player_uids jsonb NOT NULL DEFAULT '[]'::jsonb,
  explanation jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_events_created
  ON nfl_player_mapping_events (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_events_status
  ON nfl_player_mapping_events (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_events_filters
  ON nfl_player_mapping_events (observed_season, observed_week, observed_team, observed_position);

CREATE TABLE IF NOT EXISTS nfl_player_mapping_review_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mapping_event_id uuid NOT NULL REFERENCES nfl_player_mapping_events(id) ON DELETE CASCADE,
  queue_status text NOT NULL DEFAULT 'pending', -- pending|approved|rejected|resolved
  priority text NOT NULL DEFAULT 'medium', -- low|medium|high|critical
  reason text NOT NULL, -- unresolved|conflict|guardrail_high_confidence_remap
  observed_source text NOT NULL,
  observed_external_id text,
  observed_player_name text NOT NULL,
  normalized_name text NOT NULL,
  observed_team text,
  observed_position text,
  observed_season int,
  observed_week int,
  candidate_player_uids jsonb NOT NULL DEFAULT '[]'::jsonb,
  proposed_player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL,
  reviewer text,
  reviewer_notes text,
  approved_player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_review_queue_status
  ON nfl_player_mapping_review_queue (queue_status, priority, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_review_queue_filters
  ON nfl_player_mapping_review_queue (observed_season, observed_week, observed_team, observed_position);

CREATE TABLE IF NOT EXISTS nfl_player_mapping_quality_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_date date NOT NULL,
  season int NOT NULL DEFAULT -1,
  week int NOT NULL DEFAULT -1,
  resolver_version text NOT NULL,
  source_system text NOT NULL DEFAULT '',
  coverage_rate numeric NOT NULL DEFAULT 0.0,
  high_confidence_auto_map_rate numeric NOT NULL DEFAULT 0.0,
  unresolved_rate numeric NOT NULL DEFAULT 0.0,
  conflict_rate numeric NOT NULL DEFAULT 0.0,
  remap_count int NOT NULL DEFAULT 0,
  reversal_count int NOT NULL DEFAULT 0,
  source_freshness_hours numeric,
  readiness_status text NOT NULL DEFAULT 'warning', -- go|warning|no-go
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (snapshot_date, resolver_version, source_system, season, week)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_quality_snapshots_lookup
  ON nfl_player_mapping_quality_snapshots (snapshot_date DESC, resolver_version, source_system);

CREATE INDEX IF NOT EXISTS idx_nfl_player_mapping_quality_snapshots_status
  ON nfl_player_mapping_quality_snapshots (readiness_status, created_at DESC);

ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL;

ALTER TABLE nfl_player_projection_baselines
  ADD COLUMN IF NOT EXISTS player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL;

ALTER TABLE nfl_player_prop_market_snapshots
  ADD COLUMN IF NOT EXISTS player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL;

ALTER TABLE nfl_player_prop_model_edges
  ADD COLUMN IF NOT EXISTS player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL;

ALTER TABLE nfl_fantasy_weekly_projections
  ADD COLUMN IF NOT EXISTS player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_nfl_player_projection_features_uid_lookup
  ON nfl_player_projection_features_weekly (season, week, team, position, player_uid);

CREATE INDEX IF NOT EXISTS idx_nfl_player_projection_baselines_uid_lookup
  ON nfl_player_projection_baselines (season, week, team, position, model_version, player_uid);

CREATE INDEX IF NOT EXISTS idx_nfl_player_prop_market_snapshots_uid_lookup
  ON nfl_player_prop_market_snapshots (season, week, team, market_key, captured_at DESC, player_uid);

CREATE INDEX IF NOT EXISTS idx_nfl_player_prop_model_edges_uid_lookup
  ON nfl_player_prop_model_edges (season, week, market_key, confidence DESC, player_uid);

CREATE INDEX IF NOT EXISTS idx_nfl_fantasy_weekly_projections_uid_lookup
  ON nfl_fantasy_weekly_projections (season, week, scoring_profile, model_version, position, player_uid);
