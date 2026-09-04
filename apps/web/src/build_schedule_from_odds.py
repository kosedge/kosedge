"""
Build schedule.parquet from odds parquet for build_rest_travel.
Team norm via shared ncaam_identity (fail-closed; no odds_team_to_short).
Run from apps/web: python src/build_schedule_from_odds.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import ODDS_PARQUET_PATH, SCHEDULE_PATH, RAW_GAMES, ensure_dirs
from ncaam_identity import odds_name_to_team_norm


def main() -> None:
    if not ODDS_PARQUET_PATH.exists():
        print("Missing ODDS_PARQUET_PATH. Run odds ingestion first.")
        return
    ensure_dirs()
    odds = pl.read_parquet(ODDS_PARQUET_PATH)
    events = odds.unique(subset="event_id", keep="first").select(
        ["event_id", "home_team", "away_team", "commence_time"]
    )
    events = events.with_columns([
        pl.col("home_team")
        .map_elements(lambda v: odds_name_to_team_norm(v or ""), return_dtype=pl.Utf8)
        .alias("home_team_norm"),
        pl.col("away_team")
        .map_elements(lambda v: odds_name_to_team_norm(v or ""), return_dtype=pl.Utf8)
        .alias("away_team_norm"),
        pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("game_date"),
    ])
    before = len(events)
    events = events.filter(
        pl.col("home_team_norm").is_not_null() & pl.col("away_team_norm").is_not_null()
    )
    if len(events) < before:
        print(f"Omitted {before - len(events):,} events (unresolved NCAAM team identity).")
    home_rows = events.select(
        pl.col("home_team_norm").alias("team_norm"), pl.col("game_date"),
        pl.lit(True).alias("is_home"), pl.col("away_team_norm").alias("opponent_norm"),
    )
    away_rows = events.select(
        pl.col("away_team_norm").alias("team_norm"), pl.col("game_date"),
        pl.lit(False).alias("is_home"), pl.col("home_team_norm").alias("opponent_norm"),
    )
    schedule = pl.concat([home_rows, away_rows]).unique(
        subset=["team_norm", "game_date", "is_home", "opponent_norm"]
    )
    RAW_GAMES.mkdir(parents=True, exist_ok=True)
    schedule.write_parquet(SCHEDULE_PATH)
    print("Wrote", SCHEDULE_PATH, "with", len(schedule), "rows.")


if __name__ == "__main__":
    main()
