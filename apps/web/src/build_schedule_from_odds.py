"""
Build schedule.parquet from odds parquet for build_rest_travel. Same team norm as merge.
Run from apps/web: python src/build_schedule_from_odds.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import ODDS_PARQUET_PATH, SCHEDULE_PATH, RAW_GAMES, ensure_dirs

# Match merge_games_ensemble normalization
def _normalize(col_expr: pl.Expr) -> pl.Expr:
    return (
        col_expr.str.to_lowercase()
        .str.replace_all(r"\.", "")
        .str.replace_all(" st", " state")
        .str.replace_all("uconn", "connecticut")
        .str.strip_chars()
    )
ALIASES = {"unc": "north carolina", "lsu": "louisiana state", "usc": "southern california",
    "ole miss": "mississippi", "unlv": "nevada las vegas", "vcu": "virginia commonwealth",
    "smu": "southern methodist", "tcu": "texas christian", "wku": "western kentucky",
    "utsa": "texas san antonio", "unm": "new mexico"}
def _odds_team_to_short(col_expr: pl.Expr) -> pl.Expr:
    parts = col_expr.str.split(" ")
    short = pl.when(parts.list.len() >= 3).then(parts.list.head(2).list.join(" ")).otherwise(parts.list.get(0))
    normed = _normalize(short)
    out = normed
    for k, v in ALIASES.items():
        out = pl.when(out == k).then(pl.lit(v)).otherwise(out)
    return out


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
        _odds_team_to_short(pl.col("home_team")).alias("home_team_norm"),
        _odds_team_to_short(pl.col("away_team")).alias("away_team_norm"),
        pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("game_date"),
    ])
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
