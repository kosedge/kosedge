"""
Build days_rest and travel from schedule. Schedule can be built by build_schedule_from_odds.py.
Expects: team_norm, game_date, is_home, opponent_norm.
Run from apps/web: python src/build_rest_travel.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import SCHEDULE_PATH, PROCESSED, ensure_dirs

REST_TRAVEL_PATH = PROCESSED / "rest_travel.parquet"


def main() -> None:
    if not SCHEDULE_PATH.exists():
        print("No schedule. Run: python src/build_schedule_from_odds.py")
        return
    ensure_dirs()
    sched = pl.read_parquet(SCHEDULE_PATH)
    required = {"team_norm", "game_date", "is_home", "opponent_norm"}
    if not required.issubset(sched.columns):
        print("Schedule needs columns: team_norm, game_date, is_home, opponent_norm")
        return
    sched = sched.with_columns(pl.col("game_date").cast(pl.Date))
    sched = sched.sort(["team_norm", "game_date"])
    sched = sched.with_columns(
        (pl.col("game_date") - pl.col("game_date").shift(1).over("team_norm")).dt.total_days().alias("days_since_last")
    )
    home_games = sched.filter(pl.col("is_home")).select(
        pl.col("team_norm").alias("home_team_norm"),
        pl.col("opponent_norm").alias("away_team_norm"),
        pl.col("game_date"),
        pl.col("days_since_last").alias("days_rest_home"),
    )
    away_games = sched.filter(~pl.col("is_home")).select(
        pl.col("opponent_norm").alias("home_team_norm"),
        pl.col("team_norm").alias("away_team_norm"),
        pl.col("game_date"),
        pl.col("days_since_last").alias("days_rest_away"),
    )
    rest = home_games.join(
        away_games,
        on=["home_team_norm", "away_team_norm", "game_date"],
        how="inner",
    )
    if "travel_miles_away" not in rest.columns:
        rest = rest.with_columns(pl.lit(None).cast(pl.Float64).alias("travel_miles_away"))
    rest.write_parquet(REST_TRAVEL_PATH)
    print("Wrote REST_TRAVEL_PATH. Join to merge on home_team_norm, away_team_norm, game_date.")


if __name__ == "__main__":
    main()
