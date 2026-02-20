"""
Audit pipeline data usage: counts at each stage and where rows are dropped.
Run from apps/web: python src/audit_data_usage.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_GAMES, ODDS_PARQUET_PATH, ACTUAL_MARGINS_PATH, FULL_ENSEMBLE_RATINGS_PATH, MERGED_GAMES_PATH


def main() -> None:
    print("=" * 60)
    print("DATA USAGE AUDIT")
    print("=" * 60)

    # ---- 1. Game results (raw CSVs) ----
    espn_files = sorted(RAW_GAMES.glob("espn_cbb_games_*.csv"))
    sportsref_files = sorted(RAW_GAMES.glob("sportsref_cbb_games_*.csv")) + sorted(
        RAW_GAMES.glob("sportsref_cbb_schedule_results_*.csv")
    )
    result_files = espn_files + sportsref_files

    total_result_rows = 0
    by_file = {}
    for fp in result_files:
        try:
            df = pl.read_csv(fp, truncate_ragged_lines=True)
            # Require score-like columns
            pts_cols = [c for c in df.columns if "PTS" in str(c).upper() or "pts" in str(c)]
            if len(pts_cols) >= 2:
                n = df.filter(pl.col(pts_cols[0]).is_not_null() & pl.col(pts_cols[1]).is_not_null()).height
            else:
                n = len(df)
            by_file[fp.name] = n
            total_result_rows += n
        except Exception as e:
            by_file[fp.name] = f"error: {e}"

    print("\n1. GAME RESULTS (raw CSVs)")
    print(f"   Files: {[f.name for f in result_files]}")
    for name, n in by_file.items():
        print(f"   - {name}: {n} rows")
    print(f"   Total result rows (games with scores): {total_result_rows}")

    # ---- 2. Odds ----
    odds_path = ODDS_PARQUET_PATH
    if not odds_path.exists():
        print("\n2. ODDS: file not found")
    else:
        odds = pl.read_parquet(odds_path)
        odds_unique = odds.unique(subset=["event_id"])
        print("\n2. ODDS (ncaab_historical_odds_open_close.parquet)")
        print(f"   Total rows (game × book): {len(odds)}")
        print(f"   Unique events (games): {len(odds_unique)}")
        if "commence_time" in odds.columns:
            odds_dates = odds_unique.with_columns(
                pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("d")
            )
            print(f"   Date range: {odds_dates['d'].min()} to {odds_dates['d'].max()}")

    # ---- 3. Actual margins (results matched to odds) ----
    am_path = ACTUAL_MARGINS_PATH
    if not am_path.exists():
        print("\n3. ACTUAL MARGINS: file not found")
    else:
        am = pl.read_parquet(am_path)
        print("\n3. ACTUAL MARGINS (results → odds match)")
        print(f"   Events with actual_margin: {len(am)}")
        if total_result_rows > 0:
            pct = 100 * len(am) / total_result_rows if total_result_rows else 0
            print(f"   vs total result rows: {len(am)} / {total_result_rows} ({pct:.1f}% of result rows matched to an odds event)")
        if odds_path.exists():
            pct_odds = 100 * len(am) / len(odds_unique) if len(odds_unique) else 0
            print(f"   vs unique odds events: {len(am)} / {len(odds_unique)} ({pct_odds:.1f}% of odds events have a result)")

    # ---- 4. Ratings ----
    ratings_path = FULL_ENSEMBLE_RATINGS_PATH
    if not ratings_path.exists():
        print("\n4. RATINGS: full_ensemble_ratings.parquet not found")
    else:
        ratings = pl.read_parquet(ratings_path)
        print("\n4. RATINGS (full_ensemble_ratings.parquet)")
        print(f"   Team-season rows: {len(ratings)}")
        if "year" in ratings.columns:
            print(f"   Seasons: {sorted(ratings['year'].unique().to_list())}")

    # ---- 5. Merged output ----
    merged_path = MERGED_GAMES_PATH
    if not merged_path.exists():
        print("\n5. MERGED: file not found")
    else:
        merged = pl.read_parquet(merged_path)
        merged_one = merged.unique(subset=["event_id"], keep="first")

        missing_home = merged_one.filter(pl.col("adjem").is_null()).height
        missing_away = merged_one.filter(pl.col("adjem_away").is_null()).height
        has_both = merged_one.filter(pl.col("adjem").is_not_null() & pl.col("adjem_away").is_not_null()).height
        has_actual = merged_one.filter(pl.col("actual_margin").is_not_null()).height

        print("\n5. MERGED (merged_games_with_odds_and_ratings.parquet)")
        print(f"   Rows (game × book): {len(merged)}")
        print(f"   Unique events: {len(merged_one)}")
        print(f"   Events with BOTH home and away ratings: {has_both} ({100*has_both/len(merged_one):.1f}%)")
        print(f"   Events missing home rating: {missing_home}")
        print(f"   Events missing away rating: {missing_away}")
        print(f"   Events with actual_margin (for backtest): {has_actual}")

    # ---- 6. Summary / "all data used?" ----
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if total_result_rows and am_path.exists():
        unmatched_results = total_result_rows - len(am)
        print(f"Result rows that did NOT match any odds event: ~{unmatched_results} (different date/team name or odds not fetched for that date)")
    if odds_path.exists() and merged_path.exists():
        unmerged_events = len(odds_unique) - len(merged_one)
        print(f"Odds events not in merged: {unmerged_events} (should be 0; merge is left join odds to ratings)")
    if ratings_path.exists() and merged_path.exists():
        # Team-seasons that appear in merged (used at least once)
        used_team_seasons = set()
        for r in merged_one.iter_rows(named=True):
            if r.get("adjem") is not None:
                used_team_seasons.add((r.get("home_team_norm"), r.get("season")))
            if r.get("adjem_away") is not None:
                used_team_seasons.add((r.get("away_team_norm"), r.get("season")))
        print(f"Rating team-seasons used in merged: {len(used_team_seasons)} (of {len(ratings)} in file)")
    print()


if __name__ == "__main__":
    main()
