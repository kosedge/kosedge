CREATE TABLE IF NOT EXISTS odds_api_credit_ledger (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint text NOT NULL,
  sport_key text NOT NULL,
  request_signature text NOT NULL,
  requested_at timestamptz NOT NULL,
  request_params jsonb NOT NULL,
  status text NOT NULL,
  source_key text,
  credits_last integer,
  credits_used integer,
  credits_remaining integer,
  events_count integer NOT NULL DEFAULT 0,
  response_timestamp timestamptz,
  response_previous_timestamp timestamptz,
  response_next_timestamp timestamptz,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_odds_api_credit_ledger_sport_time
ON odds_api_credit_ledger (sport_key, requested_at DESC);

CREATE TABLE IF NOT EXISTS odds_api_request_cache (
  request_signature text PRIMARY KEY,
  endpoint text NOT NULL,
  sport_key text NOT NULL,
  request_params jsonb NOT NULL,
  status text NOT NULL,
  source_key text,
  credits_last integer,
  credits_used integer,
  credits_remaining integer,
  events_count integer NOT NULL DEFAULT 0,
  response_timestamp timestamptz,
  response_previous_timestamp timestamptz,
  response_next_timestamp timestamptz,
  last_error text,
  last_requested_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
