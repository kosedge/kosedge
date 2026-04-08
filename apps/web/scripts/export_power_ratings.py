"""
Export power ratings for the web app (CBB from full_ensemble_ratings).
Reads full_ensemble_ratings.parquet, writes data/processed/power_ratings_ncaam.json.
Run from apps/web: python scripts/export_power_ratings.py
"""
import json
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import FULL_ENSEMBLE_RATINGS_PATH, PROCESSED

PROCESSED.mkdir(parents=True, exist_ok=True)


def export_ncaam() -> None:
    if not FULL_ENSEMBLE_RATINGS_PATH.exists():
        print(f"Missing {FULL_ENSEMBLE_RATINGS_PATH}. Run build_ensemble_ratings.py first.")
        return

    df = pl.read_parquet(FULL_ENSEMBLE_RATINGS_PATH)
    # Use latest year in data (current season)
    max_year = int(df["year"].max()) if "year" in df.columns else None
    if max_year is not None:
        df = df.filter(pl.col("year") == max_year)

    # Composite rating: prefer adjem; else net_torvik; else barthag
    if "adjem" in df.columns:
        rating_col = "adjem"
    elif "net_torvik" in df.columns:
        rating_col = "net_torvik"
    elif "barthag" in df.columns:
        rating_col = "barthag"
    else:
        print("No rating column (adjem, net_torvik, barthag) found.")
        return

    df = df.sort(rating_col, descending=True).with_row_index("rank").with_columns(
        (pl.col("rank") + 1).alias("rank")
    )
    ratings = []
    for r in df.iter_rows(named=True):
        team = r.get("team_norm") or ""
        if isinstance(team, str):
            team = team.replace("_", " ").strip()
        rating_val = r.get(rating_col)
        ratings.append({
            "rank": int(r["rank"]),
            "team": team,
            "teamNorm": r.get("team_norm"),
            "rating": round(float(rating_val), 2) if rating_val is not None else 0,
            "adjem": round(float(r["adjem"]), 2) if r.get("adjem") is not None else None,
            "torvik": round(float(r["net_torvik"]), 2) if r.get("net_torvik") is not None else None,
            "barthag": round(float(r["barthag"]), 2) if r.get("barthag") is not None else None,
            "year": int(r["year"]) if r.get("year") is not None else None,
        })

    out_path = PROCESSED / "power_ratings_ncaam.json"
    with open(out_path, "w") as f:
        json.dump({"ratings": ratings}, f, indent=2)
    print(f"Wrote {out_path} with {len(ratings)} teams" + (f" (year={max_year})." if max_year else "."))


if __name__ == "__main__":
    export_ncaam()
