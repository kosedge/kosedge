-- 002_mlb_engine.sql
-- MLB simulation context + market projection outputs.

create table if not exists mlb_game_context (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid not null references games(id) on delete cascade,
  source text not null default 'mlb-stats-api',

  -- schedule / roster context
  probable_pitcher_home text,
  probable_pitcher_away text,
  lineup_confirmed boolean not null default false,

  -- environment context
  umpire_home_plate text,
  weather_source text,
  weather_temp_f numeric(6,2),
  weather_wind_mph numeric(6,2),
  weather_wind_dir_deg numeric(6,2),
  weather_humidity_pct numeric(6,2),
  park_factor_runs numeric(6,4),

  -- extra features for later model versions
  context jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (game_id)
);

create index if not exists idx_mlb_game_context_game on mlb_game_context (game_id);
create index if not exists idx_mlb_game_context_updated on mlb_game_context (updated_at desc);

create table if not exists mlb_market_projections (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid not null references games(id) on delete cascade,
  model_version text not null,
  simulation_count int not null default 2000,

  -- core market outputs
  f5_home_win_prob numeric(7,6) not null,
  fg_home_win_prob numeric(7,6) not null,
  f5_total_mean numeric(8,4) not null,
  fg_total_mean numeric(8,4) not null,

  -- fair line outputs
  fair_f5_home_ml int not null,
  fair_fg_home_ml int not null,
  fair_f5_total numeric(8,4) not null,
  fair_fg_total numeric(8,4) not null,

  -- diagnostics and future features
  projection jsonb,

  created_at timestamptz not null default now()
);

create index if not exists idx_mlb_market_proj_game on mlb_market_projections (game_id, created_at desc);
create index if not exists idx_mlb_market_proj_model on mlb_market_projections (model_version, created_at desc);
