-- 053_book_ledger.sql
-- The Book — multi-sport pick/lean/pass ledger.
-- Primary metric: CLV. Unit ROI = plays + booked only (leans units=0).
-- Settled rows are immutable; corrections are new events.

CREATE TABLE IF NOT EXISTS book_ledger (
  book_id text PRIMARY KEY,
  sport text NOT NULL,
  season int NOT NULL,
  week_or_slate text NOT NULL,
  game_id text NOT NULL,
  home text NOT NULL,
  away text NOT NULL,
  type text NOT NULL CHECK (type IN ('play', 'lean', 'pass')),
  market text NOT NULL CHECK (market IN ('spread', 'total', 'ml', 'prop')),
  side text NOT NULL,
  line numeric,
  price numeric,
  posted_at timestamptz NOT NULL,
  kei_at_post jsonb NOT NULL DEFAULT '{}'::jsonb,
  market_at_post jsonb NOT NULL DEFAULT '{}'::jsonb,
  market_source text,
  close_line numeric,
  close_price numeric,
  close_at timestamptz,
  clv numeric,
  units numeric NOT NULL DEFAULT 0,
  result text NOT NULL DEFAULT 'pending'
    CHECK (result IN ('pending', 'win', 'loss', 'push', 'void')),
  pnl_units numeric,
  stake_flag text NOT NULL DEFAULT 'paper'
    CHECK (stake_flag IN ('paper', 'booked')),
  actor text,
  confirmation text,
  info_overlap text,
  rest_flag text,
  weather_flag text,
  late_post boolean NOT NULL DEFAULT false,
  post_timing text,
  notes_ref text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  settled_at timestamptz
);

-- Idempotent natural key (sport, game_id, market, side, posted_at, type)
CREATE UNIQUE INDEX IF NOT EXISTS uq_book_ledger_natural
  ON book_ledger (sport, game_id, market, side, posted_at, type);

CREATE INDEX IF NOT EXISTS idx_book_ledger_sport_slate
  ON book_ledger (sport, week_or_slate, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_book_ledger_pending
  ON book_ledger (sport, result) WHERE result = 'pending';

CREATE INDEX IF NOT EXISTS idx_book_ledger_game
  ON book_ledger (game_id, sport);
