"""
Fetch as-of-date ratings for CBB (no look-ahead bias).
KenPom: set KENPOM_API_KEY and optional KENPOM_BASE_URL; weekly snapshots written to KENPOM_ARCHIVE_PATH.
Torvik: uses cbbdata if installed (pip install cbbdata); writes TORVIK_ARCHIVE_PATH.
Run from apps/web: python src/fetch_ratings_archive.py
"""
import os
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import (
    RATINGS_ARCHIVE_DIR,
    KENPOM_ARCHIVE_PATH,
    TORVIK_ARCHIVE_PATH,
    ensure_dirs,
)

# Match build_ensemble_ratings / merge team normalization
def _normalize_team(name: str) -> str:
    n = name.lower().replace(".", "").replace(" st", " state").replace("uconn", "connecticut").strip()
    return n


def _fetch_kenpom_as_of(date_str: str, api_key: str, base_url: str) -> pl.DataFrame | None:
    import urllib.request
    url = f"{base_url.rstrip('/')}?endpoint=archive&d={date_str}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            import json
            data = json.load(r)
        if not data:
            return None
        df = pl.DataFrame(data)
        if "teamname" not in df.columns and "Team" in df.columns:
            df = df.rename({"Team": "teamname"})
        if "teamname" not in df.columns:
            return None
        df = df.with_columns([
            pl.col("teamname").map_batches(lambda s: pl.Series([_normalize_team(x) for x in s])).alias("team_norm"),
            pl.lit(date_str).alias("as_of_date"),
        ])
        return df
    except Exception as e:
        print("KenPom", date_str, e)
        return None


def fetch_kenpom_archive() -> None:
    api_key = os.environ.get("KENPOM_API_KEY")
    base_url = os.environ.get("KENPOM_BASE_URL", "https://kenpom.com/api.php")
    if not api_key:
        print("Set KENPOM_API_KEY to fetch KenPom archive. Skipping.")
        return
    from datetime import date, timedelta
    out = []
    for year in range(2016, 2026):
        # Weekly from Nov 1 to Apr 15
        start = date(year - 1, 11, 1)
        end = date(year, 4, 15)
        d = start
        while d <= end:
            date_str = d.isoformat()
            df = _fetch_kenpom_as_of(date_str, api_key, base_url)
            if df is not None and len(df) > 0:
                out.append(df)
            d += timedelta(days=7)
    if not out:
        print("No KenPom archive rows fetched.")
        return
    combined = pl.concat(out)
    combined = combined.with_columns(pl.col("as_of_date").str.to_date())
    combined.write_parquet(KENPOM_ARCHIVE_PATH)
    print("Wrote KenPom archive:", KENPOM_ARCHIVE_PATH, len(combined), "rows.")


def fetch_torvik_archive() -> None:
    try:
        from cbbdata import cbd_torvik_ratings_archive
    except ImportError:
        print("Install cbbdata for Torvik archive: pip install cbbdata. Skipping.")
        return
    from datetime import date, timedelta
    out = []
    for year in range(2016, 2026):
        start = date(year - 1, 11, 1)
        end = date(year, 4, 15)
        d = start
        while d <= end:
            try:
                df = cbd_torvik_ratings_archive(year, d)
                if df is not None and len(df) > 0:
                    if "team" in df.columns:
                        df = pl.from_pandas(df) if hasattr(df, "to_pandas") else pl.DataFrame(df)
                        df = df.with_columns([
                            pl.col("team").map_batches(lambda s: pl.Series([_normalize_team(x) for x in s])).alias("team_norm"),
                            pl.lit(d).alias("as_of_date"),
                        ])
                        out.append(df)
            except Exception as e:
                pass
            d += timedelta(days=7)
    if not out:
        print("No Torvik archive rows.")
        return
    combined = pl.concat(out)
    combined.write_parquet(TORVIK_ARCHIVE_PATH)
    print("Wrote Torvik archive:", TORVIK_ARCHIVE_PATH, len(combined), "rows.")


def main() -> None:
    ensure_dirs()
    fetch_kenpom_archive()
    fetch_torvik_archive()


if __name__ == "__main__":
    main()
