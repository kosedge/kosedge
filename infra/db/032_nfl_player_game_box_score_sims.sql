-- 032_nfl_player_game_box_score_sims.sql
--
-- Real per-game, per-player box-score Monte Carlo output. Distinct from
-- nfl_player_projection_baselines (a single deterministic mean+std per
-- player-week -- a *marginal* distribution): this table stores the result of
-- actually SAMPLING replicate box scores for every player on a team, where
-- within one replicate a team's implied pass/rush volume is drawn ONCE and
-- shared across every player on that team, then allocated to individual
-- players via a role-confidence-scaled Dirichlet draw around their season
-- usage shares. That preserves realistic within-game correlation (a team's
-- big passing game and its QB's/WRs' big games happen in the SAME
-- replicate, not independently), which a per-player marginal distribution
-- cannot represent. See services/model-service/src/services/
-- nfl_player_box_score_simulator.py for the engine and
-- src/tasks.py::materialize_nfl_player_box_score_sims for the writer.
--
-- Each *_dist column is a jsonb block of {mean, std, p10, p25, p50, p75, p90}
-- computed across all replicates for that stat. A handful of the most
-- commonly-queried means are also flattened into plain numeric columns for
-- simple indexed/aggregate SQL (season totals, prop screens) without having
-- to unpack jsonb every time.
CREATE TABLE IF NOT EXISTS nfl_player_game_box_score_sims (
  season integer NOT NULL,
  week integer NOT NULL,
  game_id text NOT NULL,
  team text NOT NULL,
  opponent text,
  player_id text NOT NULL,
  player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL,
  player_name text,
  position text,
  model_version text NOT NULL,
  replicate_count integer NOT NULL,
  team_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  pass_attempts_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  completions_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  pass_yards_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  pass_tds_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  rush_attempts_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  rush_yards_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  rush_tds_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  targets_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  receptions_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  receiving_yards_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  rec_tds_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  total_tds_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  fantasy_points_ppr_dist jsonb NOT NULL DEFAULT '{}'::jsonb,
  pass_yards_mean numeric,
  rush_yards_mean numeric,
  receiving_yards_mean numeric,
  receptions_mean numeric,
  total_tds_mean numeric,
  source_coverage jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (season, week, team, player_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_box_score_sims_lookup
  ON nfl_player_game_box_score_sims (season, week, team, "position");

CREATE INDEX IF NOT EXISTS idx_nfl_player_box_score_sims_uid
  ON nfl_player_game_box_score_sims (season, week, player_uid);

CREATE INDEX IF NOT EXISTS idx_nfl_player_box_score_sims_game
  ON nfl_player_game_box_score_sims (game_id);

CREATE INDEX IF NOT EXISTS idx_nfl_player_box_score_sims_updated
  ON nfl_player_game_box_score_sims (updated_at DESC);

-- Season-level aggregation of the per-game box score sims: correct
-- sum-across-real-games mean/std (assuming independence across weeks, i.e.
-- Var(season_total) = sum(Var(week)) -- the same linearity-of-expectation
-- logic player_season_totals.py already uses for means, extended here to
-- also carry a real season-level std since the per-game sim actually
-- produces one). This is DERIVED/recomputable at any time from
-- nfl_player_game_box_score_sims -- never hand-edited.
CREATE TABLE IF NOT EXISTS nfl_player_season_box_score_sims (
  season integer NOT NULL,
  team text NOT NULL,
  player_id text NOT NULL,
  player_uid uuid REFERENCES nfl_player_identities(player_uid) ON DELETE SET NULL,
  player_name text,
  position text,
  model_version text NOT NULL,
  games_aggregated integer NOT NULL DEFAULT 0,
  pass_yards_mean numeric,
  pass_yards_std numeric,
  rush_yards_mean numeric,
  rush_yards_std numeric,
  receiving_yards_mean numeric,
  receiving_yards_std numeric,
  receptions_mean numeric,
  receptions_std numeric,
  total_tds_mean numeric,
  total_tds_std numeric,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (season, team, player_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_nfl_player_season_box_score_sims_uid
  ON nfl_player_season_box_score_sims (season, player_uid);
