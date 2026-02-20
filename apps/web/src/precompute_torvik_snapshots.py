"""
Precompute weekly Torvik rating snapshots for rolling (no look-ahead) backtests.
Uses cbbdata: cbd_torvik_ratings_archive(year, date). Run cbd_login() first if required.
Run once from apps/web: python src/precompute_torvik_snapshots.py
Output: data/processed/torvik_snapshots/torvik_YYYY-MM-DD.parquet
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import TORVIK_SNAPSHOTS_DIR, ensure_dirs


def normalize_team_name(s: str) -> str:
    """Match merge_games_ensemble / build_ensemble_ratings team_norm."""
    if not s:
        return ""
    s = s.lower().replace(".", "").replace(" st", " state").replace("uconn", "connecticut").strip()
    return s


def fetch_torvik_archive(year: int, date_str: str) -> Optional[pl.DataFrame]:
    try:
        from cbbdata import cbd_torvik_ratings_archive
        df = cbd_torvik_ratings_archive(year=year, date=date_str)
        if df is None or df.empty:
            return None
        df = pl.from_pandas(df)
        df = df.rename({k: k.lower().replace(" ", "_") for k in df.columns})
        team_col = "team" if "team" in df.columns else next((c for c in df.columns if "team" in c.lower()), df.columns[0])
        if team_col in df.columns:
            df = df.with_columns(
                pl.col(team_col).map_elements(normalize_team_name, return_dtype=pl.Utf8).alias("team_norm")
            )
        df = df.with_columns(pl.lit(date_str).alias("snapshot_date"))
        return df
    except Exception as e:
        print(f"  Error {date_str} (year={year}): {e}")
        return None


def main() -> None:
    try:
        from cbbdata import cbd_torvik_ratings_archive
    except ImportError:
        print("Install cbbdata: pip install cbbdata. Skipping Torvik snapshots.")
        return
    ensure_dirs()
    start = datetime(2015, 11, 1)
    end = datetime(2025, 4, 1)
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        out_path = TORVIK_SNAPSHOTS_DIR / f"torvik_{date_str}.parquet"
        if out_path.exists():
            print(f"Skip (exists): {date_str}")
        else:
            print(f"Torvik archive: {date_str}")
            year = current.year + 1 if current.month >= 11 else current.year
            df = fetch_torvik_archive(year, date_str)
            if df is not None and len(df) > 0:
                df.write_parquet(out_path)
        current += timedelta(days=7)
        time.sleep(2)
    print("Done.")


if __name__ == "__main__":
    main()
