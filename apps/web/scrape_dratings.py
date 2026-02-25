"""
Scrape D-Ratings (dratings.com) NCAAB ratings by year.
Saves CSVs to data/raw/ratings/ (~350–365 rows per year).

Install if needed: pip install requests beautifulsoup4 pandas lxml
Run from apps/web: python scrape_dratings.py
"""
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Pipeline raw dir (same as other ingest scripts)
import sys
_WEB = Path(__file__).resolve().parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_RATINGS, ensure_dirs
ensure_dirs()
RAW_DIR = RAW_RATINGS

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

YEARS = range(2016, 2027)


def main() -> None:
    for year in YEARS:
        url = f"https://www.dratings.com/sports/ncaa-college-basketball-ratings-{year}"
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"Failed {year}: status {response.status_code}")
                time.sleep(0.5)
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                print(f"No table found for {year}")
                time.sleep(0.5)
                continue
            # lxml is faster/more robust if installed
            try:
                df = pd.read_html(str(table), flavor="lxml")[0]
            except Exception:
                df = pd.read_html(str(table))[0]
            df["year"] = year
            out_path = RAW_DIR / f"dratings_ratings_{year}.csv"
            df.to_csv(out_path, index=False)
            print(f"Saved dratings_ratings_{year}.csv ({len(df)} rows)")
        except Exception as e:
            print(f"Error {year}: {e}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
