"""
Build results.csv (event_id, home_pts, away_pts) from ESPN game CSVs + odds for actual_total in merge.
Expects data/raw/games/espn_cbb_games_*.csv with Date, Visitor, PTS, Home, PTS_2.
Run from apps/web: python src/build_results_with_totals.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import ODDS_PARQUET_PATH, RAW_GAMES, ensure_dirs

RESULTS_CSV = RAW_GAMES / "results.csv"

def _norm(s: str) -> str:
    s = s.lower().replace(".", "").replace(" st", " state").replace("uconn", "connecticut").strip()
    parts = s.split()
    short = " ".join(parts[:2]) if len(parts) >= 3 else (parts[0] if parts else "")
    aliases = {"unc": "north carolina", "lsu": "louisiana state", "usc": "southern california",
               "ole miss": "mississippi", "unlv": "nevada las vegas", "vcu": "virginia commonwealth",
               "smu": "southern methodist", "tcu": "texas christian", "wku": "western kentucky",
               "utsa": "texas san antonio", "unm": "new mexico"}
    return aliases.get(short, short)

def main() -> None:
    if not ODDS_PARQUET_PATH.exists():
        print("Missing ODDS_PARQUET_PATH.")
        return
    ensure_dirs()
    events = pl.read_parquet(ODDS_PARQUET_PATH).unique(subset="event_id", keep="first").select(
        ["event_id", "home_team", "away_team", "commence_time"]
    )
    events = events.with_columns([
        events["home_team"].map_elements(lambda x: _norm(x)).alias("home_team_norm"),
        events["away_team"].map_elements(lambda x: _norm(x)).alias("away_team_norm"),
        pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("game_date"),
    ])
    dfs = []
    for f in sorted(RAW_GAMES.glob("espn_cbb_games_*.csv")):
        df = pl.read_csv(f)
        if "Date" not in df.columns or "Home" not in df.columns or "PTS_2" not in df.columns:
            continue
        df = df.with_columns([
            pl.col("Date").str.to_date(strict=False).alias("game_date"),
            pl.col("Visitor").map_elements(lambda x: _norm(x)).alias("away_team_norm"),
            pl.col("Home").map_elements(lambda x: _norm(x)).alias("home_team_norm"),
            pl.col("PTS").cast(pl.Int32).alias("away_pts"),
            pl.col("PTS_2").cast(pl.Int32).alias("home_pts"),
        ])
        dfs.append(df.select(["game_date", "home_team_norm", "away_team_norm", "home_pts", "away_pts"]))
    if not dfs:
        print("No ESPN CSVs with Date, Home, PTS_2 found in", RAW_GAMES)
        return
    games = pl.concat(dfs).unique(subset=["game_date", "home_team_norm", "away_team_norm"], keep="first")
    results = events.join(
        games, on=["game_date", "home_team_norm", "away_team_norm"], how="inner"
    ).select(["event_id", "home_pts", "away_pts"])
    results.write_csv(RESULTS_CSV)
    print("Wrote", RESULTS_CSV, "with", len(results), "rows. Merge will use for actual_margin and actual_total.")
if __name__ == "__main__":
    main()
