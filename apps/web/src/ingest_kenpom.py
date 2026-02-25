import os
import sys
import requests
import pandas as pd
from pathlib import Path

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_RATINGS, ensure_dirs

# Use env var so the key isn't committed. Set KENPOM_API_KEY in .env or shell.
API_KEY = os.environ.get("KENPOM_API_KEY", "").strip()
BASE_URL = "https://kenpom.com/api.php"

def fetch_kenpom_year(year):
    if not API_KEY:
        print("No KENPOM_API_KEY set; skipping fetch")
        return None
    params = {"endpoint": "ratings", "y": year}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        r = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Accept either a list or a dict with e.g. "ratings" / "data"
            if isinstance(data, list) and data:
                rows = data
            elif isinstance(data, dict):
                rows = data.get("ratings") or data.get("data") or data.get("results")
                if not isinstance(rows, list):
                    rows = []
            else:
                rows = []
            if rows:
                df = pd.DataFrame(rows)
                df["year"] = year
                print(f"Year {year}: {len(df)} teams")
                return df
        print(f"Year {year}: failed ({r.status_code})")
        return None
    except Exception as e:
        print(f"Year {year}: error {e}")
        return None

dfs = []
for y in range(2016, 2027):
    df_y = fetch_kenpom_year(y)
    if df_y is not None:
        dfs.append(df_y)

if dfs:
    full_kenpom = pd.concat(dfs, ignore_index=True)
    # Basic cleaning
    full_kenpom.columns = full_kenpom.columns.str.lower().str.replace(" ", "_")
    ensure_dirs()
    output_path = RAW_RATINGS / "kenpom_ratings_2016-2026.csv"
    full_kenpom.to_csv(output_path, index=False)
    print(f"Saved {len(full_kenpom)} rows to {output_path}")
else:
    print("No data fetched")