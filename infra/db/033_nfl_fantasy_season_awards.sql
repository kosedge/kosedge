-- 033_nfl_fantasy_season_awards.sql
-- Season-long fantasy draft rankings + MVP/OPOY award projections.
--
-- nfl_fantasy_weekly_projections (020_nfl_player_props_fantasy_foundation.sql)
-- is keyed by (season, week, ...) and answers "who should I start THIS
-- week" -- it has no season-aggregate concept at all (there is no way to
-- ask it "who should I draft"), so it is not a fit for a draft board. This
-- table is the season-long counterpart: one row per (season, scoring_profile,
-- model_version, player_id), built by summing real per-week `*_mean`
-- projections across the whole season -- the same per-week-mean-summation
-- math as data_platform_nfl.player_season_totals.aggregate_weekly_projection_rows
-- (not literally shared code, since model-service has no dependency on the
-- data-platform-nfl package -- see
-- src.tasks.materialize_nfl_fantasy_season_draft_rankings and
-- docs/NFL_PROPS_FANTASY_FOUNDATION.md for the "why not import it" note).

CREATE TABLE IF NOT EXISTS nfl_fantasy_season_draft_rankings (
  season int NOT NULL,
  scoring_profile text NOT NULL, -- standard|half_ppr|ppr
  model_version text NOT NULL,
  player_id text NOT NULL,
  player_uid uuid,
  player_name text NOT NULL,
  team text,
  position text,
  games_projected int NOT NULL DEFAULT 0,
  pass_yards_total numeric,
  rush_yards_total numeric,
  receiving_yards_total numeric,
  receptions_total numeric,
  pass_tds_total numeric,
  rush_tds_total numeric,
  rec_tds_total numeric,
  total_points numeric NOT NULL,
  replacement_points numeric,
  value_over_replacement numeric,
  rank_overall int NOT NULL,
  rank_position int NOT NULL,
  tier text NOT NULL,
  is_rookie boolean NOT NULL DEFAULT false,
  rookie_year int,
  draft_number int,
  projection_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, scoring_profile, model_version, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_fantasy_season_draft_rankings_board
  ON nfl_fantasy_season_draft_rankings (season, scoring_profile, model_version, rank_overall);

CREATE INDEX IF NOT EXISTS idx_nfl_fantasy_season_draft_rankings_position
  ON nfl_fantasy_season_draft_rankings (season, scoring_profile, model_version, position, rank_position);

-- MVP / Offensive Player of the Year award projections. See
-- services/model-service/src/services/nfl_award_projections.py for the
-- full scoring methodology + rationale documented in that module's
-- docstring. `award_score`, `team_success_score`, and `stat_composite` are
-- all deliberately persisted (not just the final rank_overall) so the "why"
-- behind a ranking is inspectable, not a black box.
CREATE TABLE IF NOT EXISTS nfl_award_projections (
  season int NOT NULL,
  award text NOT NULL, -- mvp|opoy
  model_version text NOT NULL,
  player_id text NOT NULL,
  player_uid uuid,
  player_name text NOT NULL,
  team text,
  position text,
  rank_overall int NOT NULL,
  award_score numeric NOT NULL,
  team_success_score numeric,
  stat_composite numeric,
  team_expected_wins numeric,
  team_division_title_prob numeric,
  team_playoff_prob numeric,
  pass_yards_total numeric,
  rush_yards_total numeric,
  receiving_yards_total numeric,
  pass_tds_total numeric,
  rush_tds_total numeric,
  rec_tds_total numeric,
  methodology_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT NOW(),
  updated_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (season, award, model_version, player_id)
);

CREATE INDEX IF NOT EXISTS idx_nfl_award_projections_board
  ON nfl_award_projections (season, award, model_version, rank_overall);
