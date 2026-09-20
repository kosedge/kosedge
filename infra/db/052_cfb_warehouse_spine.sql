-- 052_cfb_warehouse_spine.sql
-- Immutable research-fair snapshots + backtest run registry.
-- Bulk history stays on HD parquet. Do not bulk-reload multi-decade odds into Railway.
--
-- NEVER UPDATE a research snapshot. Injury / new information = INSERT a new row
-- with a new as_of (and later a KEI reprice — KEI is not this table).
-- Production season-engine does not live-query these tables per request.

-- Insert-only research fairs. PK includes model_version + as_of + game_id so
-- the same game can be restated over time without mutating history.
CREATE TABLE IF NOT EXISTS cfb_wh_model_predictions (
  model_version text NOT NULL,
  as_of timestamptz NOT NULL,
  game_id text NOT NULL,
  season int,
  week int,
  home_team_id text,
  away_team_id text,
  fair_spread numeric,
  fair_total numeric,
  wp numeric,
  uncertainty numeric,
  available_at timestamptz,
  era_tag text,
  week_band text,
  leakage_rule text NOT NULL DEFAULT 'strictly_before_kickoff',
  source text NOT NULL DEFAULT 'cfb_warehouse_research',
  notes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (model_version, as_of, game_id)
);

CREATE INDEX IF NOT EXISTS idx_cfb_wh_model_predictions_game
  ON cfb_wh_model_predictions (season, game_id, as_of DESC);

CREATE INDEX IF NOT EXISTS idx_cfb_wh_model_predictions_version
  ON cfb_wh_model_predictions (model_version, as_of DESC);

COMMENT ON TABLE cfb_wh_model_predictions IS
  'Insert-only CFB research fairs. Never UPDATE a snapshot. Injury = new row / KEI later.';

CREATE TABLE IF NOT EXISTS cfb_wh_backtest_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id text,
  started_at timestamptz NOT NULL DEFAULT NOW(),
  finished_at timestamptz,
  model_version text,
  leakage_rule text NOT NULL DEFAULT 'strictly_before_kickoff',
  seasons int[],
  week_band text,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  notes text,
  status text NOT NULL DEFAULT 'completed',
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cfb_wh_backtest_runs_lookup
  ON cfb_wh_backtest_runs (model_version, started_at DESC);

COMMENT ON TABLE cfb_wh_backtest_runs IS
  'Walk-forward / harness run registry. Research metrics only — not a KEI publish log.';

-- Optional stubs: conference membership by season (2026 packaged map is season=0 today).
CREATE TABLE IF NOT EXISTS cfb_wh_team_seasons (
  team_id text NOT NULL,
  season int NOT NULL,
  conference text,
  division text,
  fbs boolean NOT NULL DEFAULT true,
  source text,
  available_at timestamptz,
  notes text,
  PRIMARY KEY (team_id, season)
);

COMMENT ON TABLE cfb_wh_team_seasons IS
  'Stub: conference membership by season. Do not treat the 2026 packaged map as history.';

-- Optional stubs: coaches by team-season. Not materialized this pass.
CREATE TABLE IF NOT EXISTS cfb_wh_coaches (
  team_id text NOT NULL,
  season int NOT NULL,
  coach_name text,
  role text NOT NULL DEFAULT 'hc',
  is_new_hc boolean,
  source text,
  available_at timestamptz,
  notes text,
  PRIMARY KEY (team_id, season, role)
);

COMMENT ON TABLE cfb_wh_coaches IS
  'Stub: historical coaches. Not loaded. available_at required before use as a feature.';

INSERT INTO cfb_wh_feature_registry (feature_name, notes)
VALUES
  (
    'model_predictions_immutable',
    'Research fair snapshots. PK (model_version, as_of, game_id). Never UPDATE; injury = new row.'
  ),
  (
    'backtest_runs',
    'Walk-forward / harness metadata. Not a KEI publish path.'
  ),
  (
    'team_seasons_conference_stub',
    'Conference membership by season. Stub only until realignment history is ingested.'
  ),
  (
    'coaches_stub',
    'Coach rows by team-season. Stub only. available_at required before feature use.'
  )
ON CONFLICT (feature_name) DO NOTHING;
