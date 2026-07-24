-- 039_mlb_enterprise_runline_quality.sql
-- MLB enterprise: run-line / spread fair outputs + densify ledger + quality table.

ALTER TABLE mlb_market_projections
  ADD COLUMN IF NOT EXISTS fair_fg_spread_home numeric(8,4),
  ADD COLUMN IF NOT EXISTS fair_f5_spread_home numeric(8,4),
  ADD COLUMN IF NOT EXISTS fg_home_cover_prob_run_line numeric(7,6),
  ADD COLUMN IF NOT EXISTS f5_home_cover_prob_run_line numeric(7,6),
  ADD COLUMN IF NOT EXISTS fg_margin_mean numeric(8,4),
  ADD COLUMN IF NOT EXISTS f5_margin_mean numeric(8,4);

CREATE TABLE IF NOT EXISTS mlb_model_quality_snapshots (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_date date NOT NULL,
  model_version text NOT NULL,
  pipeline_stage text NOT NULL DEFAULT 'quality_snapshot',
  sample_size int NOT NULL DEFAULT 0,
  brier_ml numeric(10,6),
  mae_total_runs numeric(10,4),
  avg_ml_clv numeric(10,6),
  avg_total_clv numeric(10,6),
  avg_spread_clv numeric(10,6),
  ece numeric(10,6),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_quality_snapshots_lookup
  ON mlb_model_quality_snapshots (model_version, pipeline_stage, created_at DESC);

CREATE TABLE IF NOT EXISTS mlb_odds_densify_runs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  sport_key text NOT NULL DEFAULT 'baseball_mlb',
  bookmakers text NOT NULL,
  markets text NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  preferred_book text NOT NULL DEFAULT 'draftkings',
  requests_attempted int NOT NULL DEFAULT 0,
  requests_skipped_cached int NOT NULL DEFAULT 0,
  snapshots_inserted int NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'ok',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_odds_densify_runs_created
  ON mlb_odds_densify_runs (created_at DESC);
