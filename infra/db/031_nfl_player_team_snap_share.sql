-- 031_nfl_player_team_snap_share.sql
-- `snap_proxy` on nfl_player_projection_features_weekly is actually a
-- *touch-share* metric (a player's involvement_plays divided by the SUM of
-- EVERY player's involvement_plays on that team that week -- QB dropbacks +
-- every RB carry + every WR/TE target, all pooled together). That's a
-- reasonable-ish signal for a skill position sharing touches with
-- teammates, but it silently breaks for QBs: a starting QB who drops back
-- ~35 times a game gets a "snap_proxy" of ~0.20-0.25, because the
-- denominator also includes every one of his teammates' rushes/targets --
-- NOT the ~1.0 that reflects him playing essentially every offensive snap.
-- Since the QB formula in nfl_player_projection_engine.py weights this
-- signal at 70%, it was the single largest cause of "passing yards are way
-- off" (top projected passer was landing at ~3,100 season yards instead of
-- a realistic 4,000+ for a real starter).
--
-- Fix: add a real, correctly-denominated snap-share column -- a player's
-- involvement relative to the TEAM'S TOTAL OFFENSIVE PLAYS that week (a
-- stable, position-agnostic count), not relative to teammates' touches.
-- For a real starting QB this correctly lands near 0.90-1.0.
ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS team_snap_share numeric;

-- Real opponent-adjusted matchup factors (see materialize_player_projection_features
-- in ingest.py): the scheduled opponent's actual defensive EPA/play allowed
-- and pass-rush pressure rate that week, relative to league average, so a
-- player facing a bad defense projects above their team-context-only
-- baseline. This is the join that was previously entirely missing --
-- player projections had no opponent awareness at all.
ALTER TABLE nfl_player_projection_features_weekly
  ADD COLUMN IF NOT EXISTS opponent_pass_defense_factor numeric,
  ADD COLUMN IF NOT EXISTS opponent_rush_defense_factor numeric;
