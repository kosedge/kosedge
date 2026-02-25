"""
Precompute weekly KenPom rating snapshots for rolling (no look-ahead) backtests.
Uses KenPom archive API: endpoint=archive&d=YYYY-MM-DD.
Run once from apps/web: python src/precompute_kenpom_snapshots.py
Takes ~1–2 hours due to API rate limiting. Output: data/processed/kenpom_snapshots/kenpom_YYYY-MM-DD.parquet
"""
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import polars as pl
import requests

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import KENPOM_SNAPSHOTS_DIR, ensure_dirs


def _load_dotenv() -> None:
    for name in (".env.local", ".env"):
        path = _WEB / name
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        break


BASE_URL = "https://kenpom.com/api.php"


def normalize_team_name(s: str) -> str:
    """Match merge_games_ensemble / build_ensemble_ratings team_norm."""
    if not s:
        return ""
    s = s.lower().replace(".", "").replace(" st", " state").replace("uconn", "connecticut").strip()
    return s


def fetch_kenpom_archive(date_str: str, api_key: str) -> Optional[pl.DataFrame]:
    params = {"endpoint": "archive", "d": date_str}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(BASE_URL, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if data:
                df = pl.DataFrame(data)
                df = df.rename({k: k.lower().replace(" ", "_") for k in df.columns})
                team_col = "teamname" if "teamname" in df.columns else "team"
                if team_col not in df.columns and df.width > 0:
                    team_col = df.columns[0]
                if team_col in df.columns:
                    df = df.with_columns(
                        pl.col(team_col).map_elements(normalize_team_name, return_dtype=pl.Utf8).alias("team_norm")
                    )
                df = df.with_columns(pl.lit(date_str).alias("snapshot_date"))
                return df
    except Exception as e:
        print(f"Error for {date_str}: {e}")
    return None


def main() -> None:
    _load_dotenv()
    api_key = os.environ.get("KENPOM_API_KEY", "").strip()
    if not api_key:
        print("Set KENPOM_API_KEY in environment or .env.local. Skipping.")
        return
    ensure_dirs()
    start_date = datetime(2015, 11, 1)
    end_date = datetime(2025, 4, 1)
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        out_path = KENPOM_SNAPSHOTS_DIR / f"kenpom_{date_str}.parquet"
        if out_path.exists():
            print(f"Skip (exists): {date_str}")
        else:
            print(f"Fetching KenPom archive: {date_str}")
            df = fetch_kenpom_archive(date_str, api_key)
            if df is not None and len(df) > 0:
                df.write_parquet(out_path)
            else:
                print(f"  No data for {date_str}")
        current += timedelta(days=7)
        time.sleep(1.5)
    print("Done.")


if __name__ == "__main__":
    main()
