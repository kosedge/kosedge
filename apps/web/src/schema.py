"""
Schema contracts for pipeline parquet outputs. Use to validate columns (and optional dtypes).
"""
from __future__ import annotations

from typing import Any

import polars as pl

# Required columns per output (subset that downstream code relies on)
FULL_RATINGS_COLUMNS = {"season", "team_norm", "adjem", "sos"}
FULL_ENSEMBLE_RATINGS_COLUMNS = {"year", "team_norm", "adjem", "sos", "adjoe", "adjde", "net_torvik", "barthag", "bpr"}
ODDS_PARQUET_COLUMNS = {"event_id", "home_team", "away_team", "commence_time", "book", "open_spread_home", "close_spread_home", "open_total", "close_total"}
ACTUAL_MARGINS_COLUMNS = {"event_id", "actual_margin"}
GAMES_WITH_EDGES_COLUMNS = {"event_id", "model_spread", "close_spread_home", "edge_home", "edge_away"}
MERGED_GAMES_COLUMNS = {"event_id", "ensemble_spread", "close_spread_home", "edge_home", "edge_away", "spread_edge"}


def validate_columns(df: pl.DataFrame, required: set[str], name: str = "output") -> list[str]:
    """
    Return list of missing columns. Empty list means valid.
    """
    have = set(df.columns)
    missing = required - have
    return sorted(missing)


def assert_schema(df: pl.DataFrame, required: set[str], name: str = "output") -> None:
    """Raise ValueError if any required columns are missing."""
    missing = validate_columns(df, required, name)
    if missing:
        raise ValueError(f"{name}: missing required columns: {missing}")


def get_schema_for_path(path_name: str) -> set[str] | None:
    """Return required column set for a known output path name, or None."""
    m = {
        "full_ratings": FULL_RATINGS_COLUMNS,
        "full_ensemble_ratings": FULL_ENSEMBLE_RATINGS_COLUMNS,
        "ncaab_historical_odds_open_close": ODDS_PARQUET_COLUMNS,
        "actual_margins": ACTUAL_MARGINS_COLUMNS,
        "games_with_edges": GAMES_WITH_EDGES_COLUMNS,
        "merged_games_with_odds_and_ratings": MERGED_GAMES_COLUMNS,
    }
    return m.get(path_name)
