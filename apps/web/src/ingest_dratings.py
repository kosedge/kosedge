"""
Scrape D-Ratings (dratings.com) NCAAB ratings from the single ratings page.
Saves current-season CSV to data/raw/ratings. Run from apps/web: python src/ingest_dratings.py

How far back can we get D-Ratings?
- On the site, the Season dropdown lists 2019-20 through 2025-26 (7 seasons, back to
  season-end year 2020). There is no public API or URL query param that returns a
  different season; the dropdown is JS-driven, so a plain GET only returns the default
  (current) season.
- With this script: only the default season (e.g. 2025-26 → dratings_ratings_2026.csv).
- To fetch historical seasons (2020–2025): use browser automation (e.g. Playwright or
  Selenium) to open the page, select each season in the dropdown, and scrape the
  table; then save as dratings_ratings_YYYY.csv for each season end year.
"""
import csv
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_RATINGS, ensure_dirs

ensure_dirs()

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Default season on the page is 2025-26 -> we use end year 2026
DEFAULT_SEASON_END_YEAR = 2026
URL = "https://www.dratings.com/sports/ncaa-college-basketball-ratings/"


def _team_from_cell(text: str) -> str:
    """Extract team name from first column e.g. '1. Michigan Wolverines(25-1)' or link text."""
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    # Remove leading "N. " (rank)
    s = re.sub(r"^\d+\.\s*", "", s)
    # Remove trailing (W-L)
    s = re.sub(r"\s*\(\d+-\d+\)\s*$", "", s).strip()
    return s


def main() -> None:
    response = requests.get(URL, headers=REQUEST_HEADERS, timeout=15)
    if response.status_code != 200:
        print(f"Failed: status {response.status_code}")
        return
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        print("No table found on page")
        return
    # Parse rows: first column = team (with rank and record), second = Overall
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2:
            ths = tr.find_all("th")
            if ths and "rank" in (ths[0].get_text() or "").lower():
                continue  # skip header row
            continue
        raw_first = (cells[0].get_text() or "").strip()
        team = _team_from_cell(raw_first)
        if not team:
            continue
        # Second cell is Overall rating (numeric)
        raw_second = (cells[1].get_text() or "").strip().replace(",", "")
        try:
            rating = float(raw_second)
        except ValueError:
            continue
        rows.append({"team": team, "dratings_rating": rating})
    if not rows:
        print("No data rows parsed")
        return
    year = DEFAULT_SEASON_END_YEAR
    out_path = RAW_RATINGS / f"dratings_ratings_{year}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["team", "dratings_rating"])
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {out_path.name} ({len(rows)} rows) for season ending {year}")


if __name__ == "__main__":
    main()
