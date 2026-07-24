-- 040_mlb_enterprise_clv_board_health.sql
-- MLB enterprise: CLV attribution (incl. spread/run-line), board health, prop stake gate.

CREATE TABLE IF NOT EXISTS mlb_clv_attribution (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  model_version text NOT NULL,
  market_code text NOT NULL, -- moneyline | total | spread
  preferred_book text,
  open_line numeric(10,4),
  close_line numeric(10,4),
  open_price_home int,
  close_price_home int,
  open_price_away int,
  close_price_away int,
  model_side text,
  clv_value numeric(12,6),
  home_team_won boolean,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (game_id, model_version, market_code)
);

-- Additive upgrades for pre-enterprise mlb_clv_attribution schemas.
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS preferred_book text;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS open_price_home int;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS close_price_home int;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS open_price_away int;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS close_price_away int;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS model_side text;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS home_team_won boolean;
ALTER TABLE mlb_clv_attribution ADD COLUMN IF NOT EXISTS payload jsonb NOT NULL DEFAULT '{}'::jsonb;
-- Older schemas required projection_id; enterprise CREATE omits it.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'mlb_clv_attribution'
      AND column_name = 'projection_id'
  ) THEN
    ALTER TABLE mlb_clv_attribution ALTER COLUMN projection_id DROP NOT NULL;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'mlb_clv_attribution_game_id_model_version_market_code_key'
  ) THEN
    ALTER TABLE mlb_clv_attribution
      ADD CONSTRAINT mlb_clv_attribution_game_id_model_version_market_code_key
      UNIQUE (game_id, model_version, market_code);
  END IF;
EXCEPTION WHEN others THEN
  -- Unique may already exist under another name; ignore.
  NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_mlb_clv_attribution_lookup
  ON mlb_clv_attribution (model_version, market_code, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mlb_clv_attribution_game
  ON mlb_clv_attribution (game_id);

CREATE TABLE IF NOT EXISTS mlb_board_health_snapshots (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_date date NOT NULL,
  model_version text NOT NULL,
  publish_ready boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_board_health_lookup
  ON mlb_board_health_snapshots (model_version, created_at DESC);

-- Explicit research-only gate for MLB player props until a pre-registered holdout clears.
CREATE TABLE IF NOT EXISTS mlb_prop_stake_policy (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  market_family text NOT NULL DEFAULT 'player_props',
  play_stake_eligible boolean NOT NULL DEFAULT false,
  reason text NOT NULL DEFAULT 'no_preregistered_holdout',
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (market_family)
);

INSERT INTO mlb_prop_stake_policy (market_family, play_stake_eligible, reason)
VALUES ('player_props', false, 'enterprise_default_research_only')
ON CONFLICT (market_family) DO UPDATE
SET play_stake_eligible = EXCLUDED.play_stake_eligible,
    reason = EXCLUDED.reason,
    updated_at = now();
