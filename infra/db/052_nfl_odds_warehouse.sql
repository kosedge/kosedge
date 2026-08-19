-- 052_nfl_odds_warehouse.sql
-- Spread belongs in market history / CLV (Edge Board actually bets it).
-- Kickoff-safe path features live on the HD parquet lake; this only extends
-- the live Postgres CLV substrate.

ALTER TABLE nfl_market_history_snapshots
  ADD COLUMN IF NOT EXISTS spread_home numeric;

COMMENT ON COLUMN nfl_market_history_snapshots.market_code IS
  'moneyline | total | spread';

COMMENT ON TABLE nfl_clv_attribution IS
  'CLV vs last legal pre-kickoff snapshot (prefer labeled close). Markets: moneyline, total, spread.';
