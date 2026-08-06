"""DDL for durable unified proof projections (Postgres)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text


def ensure_proof_projections_table(session: Any) -> None:
    """Idempotent DDL for the unified proof lake table."""
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS proof_projections (
              id uuid PRIMARY KEY,
              sport text NOT NULL,
              market_type text NOT NULL DEFAULT 'game',
              game_key text NOT NULL,
              season int NOT NULL,
              week int NOT NULL,
              home_team text NOT NULL,
              away_team text NOT NULL,
              engine_version text NOT NULL,
              projected_at timestamptz NOT NULL,
              model_spread_home numeric,
              model_total numeric,
              home_win_prob numeric,
              away_win_prob numeric,
              expected_home_score numeric,
              expected_away_score numeric,
              drivers jsonb NOT NULL DEFAULT '{}'::jsonb,
              projection jsonb NOT NULL DEFAULT '{}'::jsonb,
              close_spread_home numeric,
              close_total numeric,
              close_captured_at timestamptz,
              close_source text,
              spread_clv numeric,
              total_clv numeric,
              home_score int,
              away_score int,
              result_captured_at timestamptz,
              result_source text,
              grade_ats text,
              grade_ou text,
              grade_su text,
              payload jsonb NOT NULL DEFAULT '{}'::jsonb,
              created_at timestamptz NOT NULL DEFAULT NOW(),
              updated_at timestamptz NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_proof_proj_sport_version_projected
              ON proof_projections (sport, engine_version, projected_at DESC)
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_proof_proj_sport_projected
              ON proof_projections (sport, projected_at DESC)
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_proof_proj_season_week
              ON proof_projections (sport, season, week)
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_proof_proj_game_key
              ON proof_projections (game_key, projected_at DESC)
            """
        )
    )
