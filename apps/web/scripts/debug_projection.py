"""
Audit full_ensemble_ratings and (optional) odds team names to find missing columns
and name mismatches that cause extreme spreads or fixed 140 O/U.

Run from apps/web: python scripts/debug_projection.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import (
    FULL_ENSEMBLE_RATINGS_PATH,
    ODDS_PARQUET_PATH,
    PROCESSED,
)

def main() -> None:
    if not FULL_ENSEMBLE_RATINGS_PATH.exists():
        print(f"Missing {FULL_ENSEMBLE_RATINGS_PATH}. Run build_ensemble_ratings.py first.")
        return

    ratings = pl.read_parquet(FULL_ENSEMBLE_RATINGS_PATH)
    n = len(ratings)
    print("=== full_ensemble_ratings.parquet ===")
    print(f"Rows (team-year): {n}")
    print(f"Columns: {ratings.columns}")

    # Null counts for key columns (spread + total)
    spread_cols = ["adjem", "net_torvik", "barthag", "bpr", "haslam_net"]
    total_cols = ["adjt", "adjoe", "adjde"]
    for col in spread_cols + total_cols:
        if col in ratings.columns:
            nulls = ratings[col].null_count()
            pct = 100.0 * nulls / n if n else 0
            print(f"  {col}: {nulls} null ({pct:.1f}%)")
        else:
            print(f"  {col}: column missing")

    # Sample team_norm (for name matching)
    print("\nRatings team_norm sample (first 25):")
    if "team_norm" in ratings.columns:
        uniq = ratings["team_norm"].unique().head(25)
        for t in uniq:
            print(f"  {t}")
    print(f"  ... ({ratings['team_norm'].n_unique()} unique teams)")

    # Odds team names (if historical parquet exists) for name comparison
    if ODDS_PARQUET_PATH.exists():
        odds = pl.read_parquet(ODDS_PARQUET_PATH)
        if "home_team" in odds.columns:
            odds_teams = odds["home_team"].unique().head(25)
            print("\nOdds home_team sample (first 25):")
            for t in odds_teams:
                print(f"  {t}")
        if "away_team" in odds.columns:
            print("\nOdds away_team sample (first 10):")
            for t in odds["away_team"].unique().head(10):
                print(f"  {t}")
    else:
        print("\nNo ODDS_PARQUET_PATH; skip odds team sample.")

    # Latest year coverage
    if "year" in ratings.columns:
        latest = int(ratings["year"].max())
        r_latest = ratings.filter(pl.col("year") == latest)
        print(f"\nLatest year in ratings: {latest} ({len(r_latest)} teams)")
        for col in spread_cols + total_cols:
            if col in r_latest.columns:
                non_null = r_latest[col].drop_nulls().len()
                print(f"  {col}: {non_null} non-null in {latest}")

    print("\nDone. Fix: ensure Torvik/KenPom ingest has adjoe, adjde, adjt for totals; clip diffs in projection for sane spreads.")


if __name__ == "__main__":
    main()
