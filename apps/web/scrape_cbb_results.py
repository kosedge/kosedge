"""
Scrape Sports-Reference CBB schedule/results by season.
Saves one CSV per season to data/raw/games/ as sportsref_cbb_games_{yr}.csv.

Uses .../seasons/men/{yr}-schedule.html when available (2016–2021). For 2022+, that URL
often returns 404 (Sports-Reference removed the full-season schedule page). We try the
season summary page as fallback; if it has no schedule table, we skip with a message.

Typical columns: Date, Type, Visitor/Neutral, PTS, Home/Neutral, PTS, etc. Margins are
derived later by build_actual_margins.py (matches to odds → actual_margins.parquet).

Install: pip install requests beautifulsoup4 pandas lxml
Run from apps/web: python scrape_cbb_results.py
"""
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Pipeline raw dir (same as build_actual_margins / other ingest scripts)
import sys
_WEB = Path(__file__).resolve().parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_GAMES, ensure_dirs
ensure_dirs()
RAW_DIR = RAW_GAMES

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# End years: 2016 = 2015-16 season. -schedule.html exists for 2016–2021; 2022+ often 404.
YEARS = range(2016, 2026)

SLEEP_SECONDS = 4

URL_SCHEDULE = "https://www.sports-reference.com/cbb/seasons/men/{yr}-schedule.html"
URL_SEASON = "https://www.sports-reference.com/cbb/seasons/men/{yr}.html"


def _parse_and_save(table, yr: int) -> bool:
    """Parse schedule table and save CSV. Returns True if saved."""
    if not table:
        return False
    dfs = pd.read_html(str(table))
    if not dfs:
        return False
    df = dfs[0]
    df["season_end_year"] = yr

    def _flatten(col):
        if isinstance(col, tuple):
            return "_".join(str(c).strip() for c in col if str(c) != "nan").strip("_")
        return str(col).strip()

    df.columns = [_flatten(col) for col in df.columns.values]
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.dropna(how="all", axis=1)
    df = df.dropna(how="all", axis=0)

    out_path = RAW_DIR / f"sportsref_cbb_games_{yr}.csv"
    df.to_csv(out_path, index=False)
    print(f"Success! Saved {len(df)} games to {out_path}")
    return True


def main() -> None:
    for yr in YEARS:
        primary_url = URL_SCHEDULE.format(yr=yr)
        print(f"Fetching {yr} season ({primary_url})...")
        try:
            response = requests.get(primary_url, headers=HEADERS, timeout=15)
            if response.status_code == 404:
                fallback_url = URL_SEASON.format(yr=yr)
                print(f"  404 on schedule URL, trying season page: {fallback_url}")
                r2 = requests.get(fallback_url, headers=HEADERS, timeout=15)
                r2.raise_for_status()
                soup = BeautifulSoup(r2.text, "html.parser")
                table = soup.find("table", id="schedule")
                if not _parse_and_save(table, yr):
                    print(f"  No schedule table for {yr}. Sports-Reference removed full-season schedule for 2022+. Use another source for those seasons.")
            else:
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table", id="schedule")
                if not _parse_and_save(table, yr):
                    print(f"No 'schedule' table found on {primary_url} — page structure may have changed.")

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error {e.response.status_code} for {yr}: {primary_url}")
        except requests.exceptions.RequestException as e:
            print(f"Request error for {yr}: {e}")
        except Exception as e:
            print(f"General error for {yr}: {e}")

        time.sleep(SLEEP_SECONDS)

    print("Scraping complete! Check data/raw/games/ for sportsref_cbb_games_*.csv")
    print("Next: python src/build_actual_margins.py to match to odds and create actual_margins.parquet.")


if __name__ == "__main__":
    main()
