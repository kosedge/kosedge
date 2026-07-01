-- 009_mlb_holdout_profiles.sql
-- Persist common-sample holdout comparisons used for MLB challenger promotion.

CREATE TABLE IF NOT EXISTS mlb_model_holdout_profiles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_date date NOT NULL,
  base_model_version text NOT NULL,
  challenger_model_version text NOT NULL,
  lookback_days int NOT NULL,
  common_sample_size int NOT NULL DEFAULT 0,
  bucket_count int NOT NULL DEFAULT 0,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_holdout_profiles_lookup
  ON mlb_model_holdout_profiles (
    run_date DESC,
    base_model_version,
    challenger_model_version,
    created_at DESC
  );