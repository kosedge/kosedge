-- 006_mlb_premium_context.sql
-- Premium-context additions for bullpen availability.

ALTER TABLE mlb_game_context
  ADD COLUMN IF NOT EXISTS bullpen_availability_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS bullpen_availability_away numeric(6,4);
