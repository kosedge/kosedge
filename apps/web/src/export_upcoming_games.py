"""
Export upcoming NCAAM games with model edges for use in writeups.

Reads merged_games_with_odds_and_ratings.parquet and writes a compact JSON
for the next N days under data/processed/upcoming_ncaam_games.json.

Run from apps/web:
  python src/export_upcoming_games.py
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH, PROCESSED  # type: ignore


def main(days_ahead: int = 2) -> None:
    if not MERGED_GAMES_PATH.exists():
        print(f"Missing {MERGED_GAMES_PATH}. Run merge_games_ensemble.py first.")
        return

    df = pl.read_parquet(MERGED_GAMES_PATH)
    if "commence_time" not in df.columns:
        print("merged games missing commence_time; cannot export upcoming.")
        return

    today = date.today()
    max_date = today + timedelta(days=days_ahead)

    games = df.with_columns(
        pl.col("commence_time")
        .str.slice(0, 10)
        .str.to_date(strict=False)
        .alias("game_date")
    ).filter(
        (pl.col("game_date") >= pl.lit(today))
        & (pl.col("game_date") <= pl.lit(max_date))
    )

    if games.is_empty():
        print("No upcoming games in window; nothing to export.")
        return

    # Deduplicate by event_id (one row per game)
    games = games.unique(subset="event_id", keep="first")

    # Derive a neutral flag: both teams marked as not home (fallback: always False if we don't have venue)
    neutral = pl.lit(False).alias("neutral")

    out = games.select(
        [
            "event_id",
            "home_team",
            "away_team",
            "commence_time",
            "ensemble_spread",
            "consensus_close_spread",
            "spread_edge",
            "ensemble_total",
            "consensus_close_total",
            "total_edge",
            "days_rest_home",
            "days_rest_away",
            "travel_miles_away",
            "conference_home",
            "conference_away",
            "key_player_out_home",
            "key_player_out_away",
            neutral,
        ]
    )

    records = out.to_dicts()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "upcoming_ncaam_games.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, default=str, indent=2)
    print(f"Wrote {out_path} with {len(records)} games.")


if __name__ == "__main__":
    main()

