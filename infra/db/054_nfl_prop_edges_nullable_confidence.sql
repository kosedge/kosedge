-- 054_nfl_prop_edges_nullable_confidence.sql
-- PR 428 reliability score returns NULL for projection-only rows, one-way
-- anytime_td pricing, and other unscorable cases. Storage must accept honest
-- NULL — never fabricate a sentinel to satisfy NOT NULL or DEFAULT 0.0.
--
-- Reversible (only after backfilling or deleting NULL rows):
--   ALTER TABLE nfl_player_prop_model_edges ALTER COLUMN confidence SET DEFAULT 0.0;
--   ALTER TABLE nfl_player_prop_model_edges ALTER COLUMN confidence SET NOT NULL;

ALTER TABLE nfl_player_prop_model_edges
  ALTER COLUMN confidence DROP NOT NULL;

ALTER TABLE nfl_player_prop_model_edges
  ALTER COLUMN confidence DROP DEFAULT;
