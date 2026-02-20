"""
Join full_ratings + ncaab_historical_odds_open_close, compute model spread, edge, and backtest.
Requires: data/processed/full_ratings.parquet, data/processed/ncaab_historical_odds_open_close.parquet.
Optional: data/raw/games/results.csv or data/processed/actual_margins.parquet for actual_margin (game result).
Run from apps/web: python src/join_and_backtest.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import (
    FULL_RATINGS_PATH,
    ODDS_PARQUET_PATH,
    ACTUAL_MARGINS_PATH,
    GAMES_WITH_EDGES_PATH,
    RAW_GAMES,
)


def _norm(col_expr: pl.Expr) -> pl.Expr:
    return col_expr.str.to_lowercase().str.replace_all(r"\.", "").str.replace_all(" st", " state").str.replace_all("uconn", "connecticut").str.strip_chars()


def odds_team_to_short(col_expr: pl.Expr) -> pl.Expr:
    """Odds use 'Purdue Boilermakers'; ratings use 'purdue'. Derive short name for join."""
    parts = col_expr.str.split(" ")
    short = pl.when(parts.list.len() >= 3).then(parts.list.head(2).list.join(" ")).otherwise(parts.list.get(0))
    return _norm(short)


def game_season(commence_expr: pl.Expr) -> pl.Expr:
    """NCAAB season from commence_time: Nov+ -> next calendar year."""
    # Use date part only to avoid timezone parsing issues
    date_str = commence_expr.str.slice(0, 10)
    dt = date_str.str.to_datetime(format="%Y-%m-%d")
    year = dt.dt.year()
    month = dt.dt.month()
    return pl.when(month >= 11).then(year + 1).otherwise(year).alias("season")


def main() -> None:
    if not FULL_RATINGS_PATH.exists():
        print(f"Run build_ratings.py first. Missing {FULL_RATINGS_PATH}")
        return
    if not ODDS_PARQUET_PATH.exists():
        print(f"Run process_odds.py first. Missing {ODDS_PARQUET_PATH}")
        return

    ratings = pl.read_parquet(FULL_RATINGS_PATH)
    odds = pl.read_parquet(ODDS_PARQUET_PATH)

    # Short team names so odds match ratings (e.g. "Kansas Jayhawks" -> "kansas")
    odds = odds.with_columns([
        odds_team_to_short(pl.col("home_team")).alias("home_team_norm"),
        odds_team_to_short(pl.col("away_team")).alias("away_team_norm"),
        game_season(pl.col("commence_time")),
    ])

    # Join to get home and away ratings (one row per game-book with home/away adjem, sos)
    home_ratings = ratings.select([
        pl.col("team_norm").alias("home_team_norm"),
        pl.col("season"),
        pl.col("adjem").alias("home_adj_em"),
        pl.col("sos").alias("home_sos"),
    ])
    away_ratings = ratings.select([
        pl.col("team_norm").alias("away_team_norm"),
        pl.col("season"),
        pl.col("adjem").alias("away_adj_em"),
        pl.col("sos").alias("away_sos"),
    ])

    games = odds.join(home_ratings, on=["home_team_norm", "season"], how="left")
    games = games.join(away_ratings, on=["away_team_norm", "season"], how="left")

    # Model spread: KenPom adjem diff + home court (~3.75)
    games = games.with_columns(
        (pl.col("home_adj_em") - pl.col("away_adj_em") + 3.75).alias("model_spread")
    )
    games = games.with_columns(
        (pl.col("home_adj_em") - pl.col("away_adj_em")).alias("adj_em_diff"),
        (pl.col("home_sos") - pl.col("away_sos")).alias("sos_diff"),
    )

    # Edge: model thinks home is >4 pts better than closing line
    games = games.with_columns([
        (pl.col("model_spread") - pl.col("close_spread_home")).alias("spread_edge"),
        (pl.col("model_spread") - pl.col("close_spread_home") > 4).alias("edge_home"),
        (pl.col("close_spread_home") - pl.col("model_spread") > 4).alias("edge_away"),
    ])

    # Optional: load actual margin (home_pts - away_pts) for backtest
    actual = None
    results_csv = RAW_GAMES / "results.csv"
    if ACTUAL_MARGINS_PATH.exists():
        actual = pl.read_parquet(ACTUAL_MARGINS_PATH)
    elif results_csv.exists():
        df = pl.read_csv(results_csv)
        if "actual_margin" in df.columns and "event_id" in df.columns:
            actual = df.select(["event_id", "actual_margin"])
        elif "home_pts" in df.columns and "away_pts" in df.columns and "event_id" in df.columns:
            actual = df.with_columns(
                (pl.col("home_pts") - pl.col("away_pts")).alias("actual_margin")
            ).select(["event_id", "actual_margin"])
    if actual is not None and "event_id" in actual.columns:
        games = games.join(actual.select(["event_id", "actual_margin"]), on="event_id", how="left")
        games = games.with_columns(
            (pl.col("actual_margin") + pl.col("close_spread_home") > 0).alias("home_covered")
        ).with_columns(
            pl.when(pl.col("home_covered")).then(1.0).otherwise(-1.0).alias("units")
        )
        backtest = games.filter(pl.col("edge_home") | pl.col("edge_away"))
        if not backtest.is_empty() and "units" in backtest.columns:
            backtest = backtest.unique(subset=["event_id"], keep="first")
            summary = backtest.group_by("season").agg([
                pl.col("home_covered").mean().alias("ats_pct"),
                pl.col("units").sum().alias("total_units"),
                pl.len().alias("n_bets"),
            ])
            print("Backtest by season (edge > 4 pts), one row per game:")
            print(summary)
    else:
        games = games.with_columns(pl.lit(None).cast(pl.Float64).alias("actual_margin"))
        print("No actual_margin found. Add data/raw/games/results.csv or run build_actual_margins.py for backtest.")

    games.write_parquet(GAMES_WITH_EDGES_PATH)
    print(f"Wrote {GAMES_WITH_EDGES_PATH} with {len(games)} rows.")


if __name__ == "__main__":
    main()
