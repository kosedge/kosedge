"""
Build actual_margins.parquet from Sports-Reference/ESPN CBB game results and/or SportsData.io parquets.
Matches results to odds by date + normalized home/away team; outputs event_id, actual_margin
so merge_games_ensemble and join_and_backtest can run backtest.

Requires: ncaab_historical_odds_open_close.parquet.
Optional: sportsref_cbb_games_*.csv, espn_cbb_games_*.csv in data/raw/games/; or sportsdata_games_*.parquet in data/processed/.
Run from apps/web: python src/build_actual_margins.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_GAMES, ODDS_PARQUET_PATH, ACTUAL_MARGINS_PATH, PROCESSED, ensure_dirs

ensure_dirs()

# SportsData.io uses short abbrevs (e.g. PURD, UNC). Map to pipeline team_norm (same as odds_team_to_short).
# Expand as needed; unmapped abbrevs fall back to normalize_team(abbrev).
SPORTSDATA_ABBREV_TO_NORM: dict[str, str] = {
    "unc": "north carolina",
    "purd": "purdue",
    "kans": "kansas",
    "uk": "kentucky",
    "lsu": "louisiana state",
    "usc": "southern california",
    "ole miss": "mississippi",
    "unlv": "nevada las vegas",
    "vcu": "virginia commonwealth",
    "smu": "southern methodist",
    "tcu": "texas christian",
    "wku": "western kentucky",
    "unm": "new mexico",
    "uconn": "connecticut",
    "byu": "brigham young",
    "st johns": "st john's",
    "mtnst": "montana state",
    "jaxst": "jacksonville state",
    "char": "charlotte",
    "ccar": "coastal carolina",
}


def normalize_team(col_expr: pl.Expr) -> pl.Expr:
    """Match build_ensemble_ratings / merge_games_ensemble."""
    return (
        col_expr.str.to_lowercase()
        .str.replace_all(r"\.", "")
        .str.replace_all(" st", " state")
        .str.replace_all("uconn", "connecticut")
        .str.strip_chars()
    )


def odds_team_to_short(col_expr: pl.Expr) -> pl.Expr:
    """Odds use 'Purdue Boilermakers'; ESPN uses 'Purdue'. Derive short name for joining."""
    parts = col_expr.str.split(" ")
    # If 3+ words (e.g. 'North Carolina Tar Heels'), take first 2; else take first 1
    short = pl.when(parts.list.len() >= 3).then(parts.list.head(2).list.join(" ")).otherwise(parts.list.get(0))
    return normalize_team(short)


def sportsdata_team_to_norm(col_expr: pl.Expr) -> pl.Expr:
    """Map SportsData abbrev (e.g. PURD, IUPUI) to pipeline team_norm for odds join."""
    raw = col_expr.str.to_lowercase().str.strip_chars().str.replace_all(r"\.", "")
    out = raw
    for abbrev, norm in SPORTSDATA_ABBREV_TO_NORM.items():
        out = out.str.replace_all(abbrev, norm)
    return normalize_team(out)


def main() -> None:
    rows: list[dict] = []
    # Load results: Sports-Reference (2016–2021) and/or ESPN (2022+)
    results_files = (
        sorted(RAW_GAMES.glob("sportsref_cbb_games_*.csv"))
        + sorted(RAW_GAMES.glob("sportsref_cbb_schedule_results_*.csv"))
        + sorted(RAW_GAMES.glob("espn_cbb_games_*.csv"))
    )
    for fp in results_files:
        df = pl.read_csv(fp, truncate_ragged_lines=True, infer_schema_length=10000)
        cols = [c for c in df.columns if c is not None]
        # Common Sports-Reference: Date, Visitor/Neutral or Visitor, PTS, Home/Neutral or Home, PTS.1 (or second PTS)
        date_col = None
        for c in cols:
            if "date" in c.lower():
                date_col = c
                break
        if not date_col:
            date_col = "Date" if "Date" in cols else cols[0]
        # Visitor = away, Home = home (Sports-Reference: "Visitor/Neutral", "Home/Neutral" or "Visitor", "Home")
        visitor_col = next((c for c in cols if "visitor" in str(c).lower() and "pts" not in str(c).lower()), None)
        home_col = next((c for c in cols if "home" in str(c).lower() and "pts" not in str(c).lower()), None)
        if not visitor_col and len(cols) > 1:
            visitor_col = cols[1]
        if not home_col and len(cols) > 3:
            home_col = cols[3]
        # PTS: two columns (visitor, home) — often PTS / PTS.1 or PTS / PTS_2 after scraper flattening
        pts_cols = [c for c in cols if str(c).strip() == "PTS" or (isinstance(c, str) and c.strip().startswith("PTS"))]
        if len(pts_cols) >= 2:
            visitor_pts, home_pts = pts_cols[0], pts_cols[1]
        elif len(pts_cols) == 1 and len(cols) >= 5:
            # Assume order: Date, Visitor, PTS, Home, PTS -> cols 2 and 4
            visitor_pts = cols[2] if len(cols) > 2 else pts_cols[0]
            home_pts = cols[4] if len(cols) > 4 else pts_cols[0]
        else:
            print(f"Skip {fp.name}: could not find two PTS columns. Columns: {cols}")
            continue

        df = df.select(
            pl.col(date_col).alias("date_str"),
            pl.col(visitor_col).alias("away_team"),
            pl.col(home_col).alias("home_team"),
            pl.col(visitor_pts).cast(pl.Float64).alias("away_pts"),
            pl.col(home_pts).cast(pl.Float64).alias("home_pts"),
        ).filter(pl.col("away_pts").is_not_null() & pl.col("home_pts").is_not_null())
        df = df.with_columns(
            (pl.col("home_pts") - pl.col("away_pts")).alias("actual_margin"),
            normalize_team(pl.col("home_team")).alias("home_norm"),
            normalize_team(pl.col("away_team")).alias("away_norm"),
        )
        # Parse date: "Tue, Nov 5, 2024" or "Nov 5, 2024" or "2024-11-05"
        df = df.with_columns(
            pl.col("date_str").str.to_date(strict=False).alias("game_date")
        )
        if df["game_date"].null_count() == len(df):
            df = df.with_columns(
                pl.col("date_str").str.strptime(pl.Date, format="%Y-%m-%d", strict=False).alias("game_date")
            )
        if df["game_date"].null_count() == len(df):
            df = df.with_columns(
                pl.col("date_str").str.strptime(pl.Date, format="%a, %b %d, %Y", strict=False).alias("game_date")
            )
        if df["game_date"].null_count() == len(df):
            df = df.with_columns(
                pl.col("date_str").str.strptime(pl.Date, format="%b %d, %Y", strict=False).alias("game_date")
            )
        df = df.filter(pl.col("game_date").is_not_null())
        for r in df.iter_rows(named=True):
            rows.append({
                "game_date": r["game_date"],
                "home_norm": r["home_norm"],
                "away_norm": r["away_norm"],
                "actual_margin": r["actual_margin"],
            })

    # Load SportsData.io parquets (e.g. sportsdata_games_2025.parquet from pull_sportsdata_cbb.py).
# Note: Free-trial SportsData margins are scrambled (fuzzed). Use for backtest pipeline testing only,
# not for training the margin model or ensemble weights — use ESPN/Sports-Ref results or unscrambled data for that.
    for fp in sorted(PROCESSED.glob("sportsdata_games_*.parquet")):
        try:
            df = pl.read_parquet(fp)
            if "DateTime" not in df.columns or "HomeTeam" not in df.columns or "actual_home_margin" not in df.columns:
                continue
            df = df.filter(pl.col("Status").is_in(["Final", "F/OT"]))
            df = df.with_columns([
                pl.col("DateTime").str.slice(0, 10).str.to_date(strict=False).alias("game_date"),
                sportsdata_team_to_norm(pl.col("HomeTeam")).alias("home_norm"),
                sportsdata_team_to_norm(pl.col("AwayTeam")).alias("away_norm"),
                pl.col("actual_home_margin").cast(pl.Float64).alias("actual_margin"),
            ]).filter(pl.col("game_date").is_not_null())
            for r in df.select(["game_date", "home_norm", "away_norm", "actual_margin"]).iter_rows(named=True):
                rows.append(r)
            print(f"  Loaded {len(df)} completed games from {fp.name}")
        except Exception as e:
            print(f"  Skip {fp.name}: {e}")

    if not rows:
        print("No result rows from CSVs or sportsdata_games_*.parquet. Add data/raw/games/*.csv or run pull_sportsdata_cbb.py --results.")
        return

    # Prefer CSV results when same (game_date, home_norm, away_norm); then join to odds
    results = pl.DataFrame(rows).unique(subset=["game_date", "home_norm", "away_norm"], keep="first")

    # Load odds to get event_id and game date + home/away
    odds_path = ODDS_PARQUET_PATH
    if not odds_path.exists():
        print("Run process_odds.py first. Missing ncaab_historical_odds_open_close.parquet")
        return
    odds = pl.read_parquet(odds_path)
    odds = odds.with_columns([
        odds_team_to_short(pl.col("home_team")).alias("home_short"),
        odds_team_to_short(pl.col("away_team")).alias("away_short"),
        pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("game_date"),
    ]).unique(subset=["event_id", "home_short", "away_short", "game_date"])

    # Join: match odds (short names from "Team Mascot") to results (ESPN/Sports-Ref short names)
    merged = odds.join(
        results.select(["game_date", "home_norm", "away_norm", "actual_margin"]).rename({
            "home_norm": "home_short",
            "away_norm": "away_short",
        }),
        on=["game_date", "home_short", "away_short"],
        how="left",
    )
    out = merged.select(["event_id", "actual_margin"]).filter(pl.col("actual_margin").is_not_null()).unique(subset=["event_id"])
    out_path = ACTUAL_MARGINS_PATH
    out.write_parquet(out_path)
    print(f"Wrote {out_path} with {len(out)} events with actual_margin (CSV + SportsData matched to odds).")


if __name__ == "__main__":
    main()
