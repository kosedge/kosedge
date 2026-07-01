-- 019_nfl_enterprise_governance.sql
-- NFL enterprise runtime governance, promotion history, and portfolio audit tables.

CREATE TABLE IF NOT EXISTS nfl_model_runtime_state (
  state_key text PRIMARY KEY,
  active_model_version text NOT NULL,
  previous_model_version text,
  reason text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nfl_model_promotion_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluated_at timestamptz NOT NULL DEFAULT NOW(),
  champion_model_version text NOT NULL,
  challenger_model_version text NOT NULL,
  lookback_days int NOT NULL,
  auto_promote_requested boolean NOT NULL DEFAULT false,
  auto_promote_enabled boolean NOT NULL DEFAULT false,
  promoted boolean NOT NULL DEFAULT false,
  decision jsonb NOT NULL DEFAULT '{}'::jsonb,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_nfl_model_promotion_events_eval
  ON nfl_model_promotion_events (evaluated_at DESC);

CREATE INDEX IF NOT EXISTS idx_nfl_model_promotion_events_models
  ON nfl_model_promotion_events (champion_model_version, challenger_model_version, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS nfl_portfolio_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version text NOT NULL,
  risk_profile text NOT NULL,
  bankroll numeric NOT NULL,
  filters jsonb NOT NULL DEFAULT '{}'::jsonb,
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_portfolio_runs_created
  ON nfl_portfolio_runs (created_at DESC);

CREATE TABLE IF NOT EXISTS nfl_portfolio_recommendations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES nfl_portfolio_runs(id) ON DELETE CASCADE,
  game_id uuid REFERENCES games(id) ON DELETE SET NULL,
  market text NOT NULL,
  selection text NOT NULL,
  score numeric,
  edge_value numeric,
  recommended_stake_fraction numeric NOT NULL,
  recommended_stake_amount numeric NOT NULL,
  reason jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nfl_portfolio_recommendations_run
  ON nfl_portfolio_recommendations (run_id, recommended_stake_fraction DESC);
