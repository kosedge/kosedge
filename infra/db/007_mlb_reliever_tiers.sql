-- 007_mlb_reliever_tiers.sql
-- Adds high-leverage reliever availability context signals.

ALTER TABLE mlb_game_context
  ADD COLUMN IF NOT EXISTS bullpen_high_leverage_availability_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS bullpen_high_leverage_availability_away numeric(6,4);
