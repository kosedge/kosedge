CREATE TABLE IF NOT EXISTS nfl_supervised_model_fits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version text NOT NULL,
  train_start_season integer NOT NULL,
  train_end_season integer NOT NULL,
  train_rows integer NOT NULL,
  test_rows integer NOT NULL,
  metrics jsonb NOT NULL,
  payload jsonb NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_nfl_supervised_model_fits_lookup
ON nfl_supervised_model_fits (model_version, is_active, created_at DESC);
