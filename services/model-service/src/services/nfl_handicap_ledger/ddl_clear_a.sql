-- DEVELOPMENT_ONLY CLEAR-A schema (t4740u).
-- NOT a numbered infra/db migration. Do not apply on any env.
-- Paper 243a384e L0/L1/L4 + Spec 2 (908b21b4): append-only IF/HF/MIF.
-- No UPDATE/DELETE. Duplicate prediction_id is a hard reject.

CREATE TABLE IF NOT EXISTS nfl_handicap_forecast_ledger (
  prediction_id text PRIMARY KEY,
  layer text NOT NULL CHECK (layer IN ('L0', 'L1', 'L4')),
  forecast_label text NOT NULL CHECK (
    forecast_label IN ('independent_fair', 'handicapped_fair', 'market_informed_fair')
  ),
  game_id text NOT NULL,
  as_of_ts timestamptz NOT NULL,
  decision_ts timestamptz NOT NULL,
  capture_id text NOT NULL,
  source_snapshot_id text NOT NULL,
  registry_id text NOT NULL,
  baseline_ref text NOT NULL,
  model_version text NOT NULL,
  schema_version text NOT NULL,
  missing boolean NOT NULL DEFAULT false,
  missingness jsonb NOT NULL DEFAULT '{}'::jsonb,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT nfl_handicap_forecast_ledger_as_of_not_after_decision
    CHECK (as_of_ts <= decision_ts)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfl_handicap_forecast_ledger_identity
  ON nfl_handicap_forecast_ledger (
    layer, forecast_label, game_id, as_of_ts, capture_id, schema_version
  );

REVOKE UPDATE, DELETE ON nfl_handicap_forecast_ledger FROM PUBLIC;
