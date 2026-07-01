-- 008_mlb_lineup_offense.sql
-- Adds persisted offense, split, and lineup-strength context for MLB pricing.

ALTER TABLE mlb_game_context
  ADD COLUMN IF NOT EXISTS offense_index_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS offense_index_away numeric(6,4),
  ADD COLUMN IF NOT EXISTS offense_split_index_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS offense_split_index_away numeric(6,4),
  ADD COLUMN IF NOT EXISTS recent_form_index_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS recent_form_index_away numeric(6,4),
  ADD COLUMN IF NOT EXISTS lineup_strength_index_home numeric(6,4),
  ADD COLUMN IF NOT EXISTS lineup_strength_index_away numeric(6,4);