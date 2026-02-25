# src/real_backtest.py
"""
Deduplicated backtest: one row per game (event_id), then filter edge + actual_margin.
Run from apps/web: python src/real_backtest.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH


def main() -> None:
    df = pl.read_parquet(MERGED_PATH)

    print(f"Total rows (games × books): {len(df):,}")
    print(f"Unique event_ids: {df['event_id'].n_unique():,}")

    # Dedupe to one row per game (keep first book)
    deduped = df.unique(subset="event_id", keep="first")

    print(f"Deduped unique games: {len(deduped):,}")

    # Filter to games with actual outcome AND high edge
    backtest = deduped.filter(
        pl.col("actual_margin").is_not_null() & (pl.col("edge_home") | pl.col("edge_away"))
    )

    print(f"Games in backtest (edge + result): {len(backtest):,}")

    if len(backtest) == 0:
        print("No games meet criteria. Check edge_home/edge_away and actual_margin.")
        return

    # Bet outcome: home_cover already exists (True = home covered). We bet home when edge_home, away when edge_away.
    backtest = backtest.with_columns(
        pl.when(pl.col("edge_home"))
        .then(pl.col("home_cover"))
        .when(pl.col("edge_away"))
        .then(~pl.col("home_cover"))
        .otherwise(None)
        .alias("bet_won")
    )

    n_bets = len(backtest)
    ats_pct = backtest["bet_won"].mean()
    # +1 if bet_won else -1
    total_units_flat = backtest.with_columns(
        pl.when(pl.col("bet_won")).then(1.0).otherwise(-1.0).alias("u")
    )["u"].sum()

    print("\n=== Real Deduped Backtest (edge >4 pts) ===")
    print(f"Unique bets: {n_bets}")
    print(f"ATS hit rate: {ats_pct:.1%}")
    print(f"Total units (flat 1u): {total_units_flat:.1f}")
    print(f"ROI: {total_units_flat / n_bets * 100:.1f}%")
    print(f"Units per bet: {total_units_flat / n_bets:.2f}")

    print("\nBy season:")
    bt = backtest.with_columns(
        pl.when(pl.col("bet_won")).then(1.0).otherwise(-1.0).alias("units_one")
    )
    by_season = bt.group_by("season").agg(
        pl.len().alias("n_bets"),
        pl.col("bet_won").mean().alias("ats_pct"),
        pl.col("units_one").sum().alias("units"),
    ).with_columns((pl.col("units") / pl.col("n_bets")).alias("units_per_bet")).sort("season")
    print(by_season)


if __name__ == "__main__":
    main()
