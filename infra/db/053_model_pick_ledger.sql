-- 053_model_pick_ledger.sql
-- Sport-agnostic PLAY/LEAN ledger with unit accounting.
-- Complements proof_projections (research CLV); does not replace it.

CREATE TABLE IF NOT EXISTS model_pick_ledger (
  id uuid PRIMARY KEY,
  sport text NOT NULL,
  season int NOT NULL,
  week int NOT NULL DEFAULT 0,
  slate_id text,
  game_id text,
  game_key text NOT NULL,
  home_team text NOT NULL,
  away_team text NOT NULL,
  market_type text NOT NULL,
  side text NOT NULL,
  line_at_publish numeric,
  odds_american int NOT NULL DEFAULT -110,
  tag text NOT NULL,
  units numeric NOT NULL DEFAULT 0,
  engine_version text,
  artifact_as_of text,
  deploy_git_sha text,
  kei_version text,
  fair_line numeric,
  kei_line numeric,
  edge_pts numeric,
  confidence text,
  variance numeric,
  confirmation text,
  info_overlap text,
  line_at_close numeric,
  close_captured_at timestamptz,
  close_source text,
  clv numeric,
  open_to_close_move numeric,
  home_score int,
  away_score int,
  result_detail jsonb NOT NULL DEFAULT '{}'::jsonb,
  grade text NOT NULL DEFAULT 'pending',
  graded_at timestamptz,
  units_risked numeric NOT NULL DEFAULT 0,
  units_won numeric NOT NULL DEFAULT 0,
  units_lost numeric NOT NULL DEFAULT 0,
  units_pnl numeric NOT NULL DEFAULT 0,
  proof_projection_id uuid,
  created_by text NOT NULL DEFAULT 'desk',
  source text NOT NULL DEFAULT 'manual',
  notes text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  published_at timestamptz NOT NULL DEFAULT NOW(),
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  CONSTRAINT model_pick_ledger_tag_chk CHECK (tag IN ('PLAY', 'LEAN')),
  CONSTRAINT model_pick_ledger_grade_chk CHECK (
    grade IN ('pending', 'win', 'loss', 'push', 'void')
  ),
  CONSTRAINT model_pick_ledger_market_chk CHECK (
    market_type IN ('spread', 'total', 'moneyline', 'prop')
  ),
  CONSTRAINT model_pick_ledger_created_by_chk CHECK (
    created_by IN ('desk', 'system')
  ),
  CONSTRAINT model_pick_ledger_source_chk CHECK (
    source IN ('manual', 'kei_board', 'auto')
  )
);

CREATE INDEX IF NOT EXISTS idx_model_pick_sport_season_week
  ON model_pick_ledger (sport, season, week);

CREATE INDEX IF NOT EXISTS idx_model_pick_sport_tag_grade
  ON model_pick_ledger (sport, tag, grade);

CREATE INDEX IF NOT EXISTS idx_model_pick_engine
  ON model_pick_ledger (sport, engine_version, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_model_pick_game_key
  ON model_pick_ledger (game_key, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_model_pick_graded_at
  ON model_pick_ledger (graded_at DESC NULLS LAST);
