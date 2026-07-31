"""Ensure NBA model tables exist (CREATE IF NOT EXISTS pattern)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text


def ensure_nba_model_tables(session: Any) -> None:
    """Idempotent DDL for Phase 0/1 NBA model persistence."""
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nba_model_runtime_state (
              state_key TEXT PRIMARY KEY,
              active_model_version TEXT NOT NULL,
              previous_model_version TEXT,
              reason TEXT,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nba_game_context (
              game_id TEXT PRIMARY KEY,
              pace_home DOUBLE PRECISION,
              pace_away DOUBLE PRECISION,
              ortg_home DOUBLE PRECISION,
              ortg_away DOUBLE PRECISION,
              drtg_home DOUBLE PRECISION,
              drtg_away DOUBLE PRECISION,
              three_pt_rate_home DOUBLE PRECISION,
              three_pt_rate_away DOUBLE PRECISION,
              three_pt_pct_home DOUBLE PRECISION,
              three_pt_pct_away DOUBLE PRECISION,
              rest_days_home DOUBLE PRECISION,
              rest_days_away DOUBLE PRECISION,
              sample_games_home INTEGER,
              sample_games_away INTEGER,
              feature_pack_version TEXT,
              context JSONB,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nba_market_projections (
              id BIGSERIAL PRIMARY KEY,
              game_id TEXT NOT NULL,
              model_version TEXT NOT NULL,
              simulation_count INTEGER NOT NULL,
              home_win_prob DOUBLE PRECISION,
              total_mean DOUBLE PRECISION,
              margin_mean DOUBLE PRECISION,
              fair_home_ml INTEGER,
              fair_total DOUBLE PRECISION,
              fair_spread_home DOUBLE PRECISION,
              home_cover_prob DOUBLE PRECISION,
              worker_build_id TEXT,
              projection JSONB NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_nba_market_projections_game_created
              ON nba_market_projections (game_id, created_at DESC)
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_nba_market_projections_model_created
              ON nba_market_projections (model_version, created_at DESC)
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nba_team_rolling_features (
              team_key TEXT NOT NULL,
              as_of_date DATE NOT NULL,
              window_games INTEGER NOT NULL DEFAULT 10,
              pace DOUBLE PRECISION,
              ortg DOUBLE PRECISION,
              drtg DOUBLE PRECISION,
              three_pt_rate DOUBLE PRECISION,
              three_pt_pct DOUBLE PRECISION,
              two_pt_pct DOUBLE PRECISION,
              ft_rate DOUBLE PRECISION,
              ft_pct DOUBLE PRECISION,
              to_rate DOUBLE PRECISION,
              orb_rate DOUBLE PRECISION,
              sample_games INTEGER,
              feature_pack_version TEXT,
              payload JSONB,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              PRIMARY KEY (team_key, as_of_date, window_games)
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nba_possessions (
              id BIGSERIAL PRIMARY KEY,
              external_game_id TEXT NOT NULL,
              possession_index INTEGER NOT NULL,
              offense_team_key TEXT,
              defense_team_key TEXT,
              points INTEGER,
              ended_by TEXT,
              period INTEGER,
              clock_seconds DOUBLE PRECISION,
              events JSONB,
              source TEXT,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              UNIQUE (external_game_id, possession_index, source)
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nba_games_ingest (
              external_game_id TEXT PRIMARY KEY,
              game_date DATE,
              start_time TIMESTAMPTZ,
              home_team_key TEXT,
              away_team_key TEXT,
              home_score INTEGER,
              away_score INTEGER,
              status TEXT,
              season TEXT,
              source TEXT,
              raw JSONB,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
