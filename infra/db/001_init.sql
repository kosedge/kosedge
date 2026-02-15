-- 001_init.sql (Postgres)
-- Enterprise-ish defaults:
-- - UUID keys
-- - append-only odds snapshots
-- - constraints + indexes for performance

create extension if not exists "uuid-ossp";

-- ---------- DIMENSIONS ----------
create table if not exists sports (
  id uuid primary key default uuid_generate_v4(),
  code text not null unique,          -- 'mlb', 'nfl', 'nba', 'ncaam'
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists leagues (
  id uuid primary key default uuid_generate_v4(),
  sport_id uuid not null references sports(id),
  code text not null,                 -- 'mlb'
  name text not null,
  created_at timestamptz not null default now(),
  unique (sport_id, code)
);

create table if not exists seasons (
  id uuid primary key default uuid_generate_v4(),
  league_id uuid not null references leagues(id),
  season_year int not null,           -- 2026
  start_date date,
  end_date date,
  created_at timestamptz not null default now(),
  unique (league_id, season_year)
);

create table if not exists teams (
  id uuid primary key default uuid_generate_v4(),
  league_id uuid not null references leagues(id),
  external_id text,                   -- mlb api id (string-safe)
  abbr text not null,                 -- 'NYY'
  name text not null,                 -- 'Yankees'
  market text,                        -- 'New York'
  created_at timestamptz not null default now(),
  unique (league_id, abbr),
  unique (league_id, external_id)
);

create table if not exists players (
  id uuid primary key default uuid_generate_v4(),
  league_id uuid not null references leagues(id),
  external_id text,
  full_name text not null,
  primary_position text,              -- 'SP', 'RP', 'C', 'SS', etc.
  bats text,                          -- 'R','L','S'
  throws text,                        -- 'R','L'
  created_at timestamptz not null default now(),
  unique (league_id, external_id)
);

-- ---------- GAMES ----------
create table if not exists games (
  id uuid primary key default uuid_generate_v4(),
  season_id uuid not null references seasons(id),
  external_id text,                   -- mlb game id
  game_date date not null,
  start_time timestamptz,
  status text not null default 'scheduled',  -- scheduled/live/final
  home_team_id uuid not null references teams(id),
  away_team_id uuid not null references teams(id),
  venue_name text,
  created_at timestamptz not null default now(),
  unique (season_id, external_id),
  unique (season_id, game_date, home_team_id, away_team_id)
);

create index if not exists idx_games_date on games (game_date);
create index if not exists idx_games_start_time on games (start_time);

-- ---------- ODDS ----------
create table if not exists sportsbooks (
  id uuid primary key default uuid_generate_v4(),
  code text not null unique,          -- 'draftkings'
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists markets (
  id uuid primary key default uuid_generate_v4(),
  code text not null unique,          -- 'moneyline','spread','total'
  created_at timestamptz not null default now()
);

-- Append-only odds snapshots (time-series)
create table if not exists odds_snapshots (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid not null references games(id),
  sportsbook_id uuid not null references sportsbooks(id),
  market_id uuid not null references markets(id),

  -- pricing fields
  -- For moneyline: price_home/price_away
  price_home int,
  price_away int,

  -- For spread: spread_home + price_home, spread_away + price_away
  spread_home numeric(6,2),
  spread_away numeric(6,2),

  -- For total: total_points + over_price + under_price
  total_points numeric(6,2),
  over_price int,
  under_price int,

  captured_at timestamptz not null default now(),
  source text,                        -- odds api provider
  created_at timestamptz not null default now()
);

create index if not exists idx_odds_game_time on odds_snapshots (game_id, captured_at desc);
create index if not exists idx_odds_market_time on odds_snapshots (market_id, captured_at desc);
create index if not exists idx_odds_book on odds_snapshots (sportsbook_id);

-- Derived lines (open/close/consensus)
create table if not exists closing_lines (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid not null references games(id),
  market_id uuid not null references markets(id),

  sportsbook_id uuid references sportsbooks(id), -- null = consensus/best
  open_captured_at timestamptz,
  close_captured_at timestamptz,

  open_price_home int,
  open_price_away int,
  close_price_home int,
  close_price_away int,

  open_spread_home numeric(6,2),
  close_spread_home numeric(6,2),

  open_total_points numeric(6,2),
  close_total_points numeric(6,2),

  created_at timestamptz not null default now(),
  unique (game_id, market_id, sportsbook_id)
);

create index if not exists idx_closing_game on closing_lines (game_id);

-- ---------- MODEL OUTPUTS ----------
create table if not exists model_runs (
  id uuid primary key default uuid_generate_v4(),
  league_id uuid not null references leagues(id),
  model_name text not null default 'kosedge-mlb',
  model_version text not null,        -- '1.0.0'
  run_type text not null default 'daily', -- daily/backtest/live
  input_hash text,                    -- hash of inputs (optional)
  created_at timestamptz not null default now()
);

create index if not exists idx_model_runs_created on model_runs (created_at desc);

create table if not exists model_game_predictions (
  id uuid primary key default uuid_generate_v4(),
  model_run_id uuid not null references model_runs(id),
  game_id uuid not null references games(id),

  proj_runs_home numeric(6,3),
  proj_runs_away numeric(6,3),
  proj_total numeric(6,3),

  win_prob_home numeric(6,4),         -- 0..1
  fair_ml_home int,                   -- american odds fair value
  fair_ml_away int,

  created_at timestamptz not null default now(),
  unique (model_run_id, game_id)
);

create index if not exists idx_preds_game on model_game_predictions (game_id);

-- Model edge vs market (this is the "board")
create table if not exists model_edges (
  id uuid primary key default uuid_generate_v4(),
  model_run_id uuid not null references model_runs(id),
  game_id uuid not null references games(id),
  market_id uuid not null references markets(id),

  -- reference line used for edge calc
  ref_type text not null default 'best',  -- best/open/close/book
  sportsbook_id uuid references sportsbooks(id),

  edge numeric(8,4),                   -- e.g. model_prob - implied_prob
  ev numeric(10,6),                    -- expected value
  confidence numeric(6,3),             -- optional
  notes jsonb,                         -- tags, reasons, etc.

  created_at timestamptz not null default now(),
  unique (model_run_id, game_id, market_id, ref_type, sportsbook_id)
);

create index if not exists idx_edges_run on model_edges (model_run_id);
create index if not exists idx_edges_game on model_edges (game_id);

-- ---------- TRACKING ----------
create table if not exists bets (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid,                        -- null for "system tracking"
  game_id uuid references games(id),
  market_id uuid references markets(id),
  sportsbook_id uuid references sportsbooks(id),

  side text,                           -- 'home','away','over','under'
  price int,
  line numeric(6,2),

  stake numeric(10,2) not null,
  placed_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists bet_results (
  bet_id uuid primary key references bets(id) on delete cascade,
  status text not null,                -- won/lost/push/void/pending
  profit numeric(12,2),                -- +/-
  settled_at timestamptz,
  created_at timestamptz not null default now()
);