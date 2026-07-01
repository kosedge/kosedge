-- 005_mlb_model_governance.sql
-- Runtime active-model state + persisted alert events.

CREATE TABLE IF NOT EXISTS mlb_model_runtime_state (
  state_key text PRIMARY KEY,
  active_model_version text NOT NULL,
  previous_model_version text,
  reason text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mlb_alert_events (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  alert_type text NOT NULL,
  severity text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_alert_events_created
  ON mlb_alert_events (created_at DESC);
