"""
Scrape Haslametrics ratings (offense, defense, fingerprint, performance) per year.
Saves CSVs to data/raw. Run from repo: python -m apps.web.src.ingest_haslametrics
or from apps/web: python src/ingest_haslametrics.py (with venv + requests, beautifulsoup4).
"""
import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Browser-like headers to reduce bot blocking (site may still return 465 from automation)
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

categories = {
    "offense": "O",
    "defense": "D",
    "fingerprint": "F",
    "performance": "P",
}

years = range(2016, 2027)

# Use pipeline paths (data/raw/ratings)
import sys
_web = Path(__file__).resolve().parent.parent
if str(_web) not in sys.path:
    sys.path.insert(0, str(_web))
from pipeline_paths import RAW_RATINGS, ensure_dirs
ensure_dirs()
raw_dir = RAW_RATINGS


def main() -> None:
    for year in years:
        for cat_name, cat_param in categories.items():
            url = f"https://haslametrics.com/ratings.php?yr={year}&stat={cat_param}"
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
            time.sleep(0.5)  # be polite; reduce rate-limit / 465 blocking
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                tables = soup.find_all("table")
                chosen = None
                for table in tables:
                    rows = []
                    for tr in table.find_all("tr"):
                        row = [td.text.strip() for td in tr.find_all("td")]
                        if row:
                            rows.append(row)
                    if len(rows) < 10:
                        continue
                    headers = rows[0]
                    first_header = (headers[0] or "").strip().lower()
                    if "support" in first_header or "venmo" in first_header or "time-dependent" in first_header:
                        continue
                    data_rows = rows[1:]
                    if len(data_rows) < 50:
                        continue
                    # Require first data row to have non-empty team-like and numeric-like cells (skip layout tables)
                    first_row = data_rows[0]
                    non_empty = sum(1 for c in first_row if (c or "").strip())
                    if non_empty < 2:
                        continue
                    chosen = (headers, data_rows)
                    break
                if chosen:
                    headers, data_rows = chosen
                    file_name = f"haslametrics_{cat_name}_{year}.csv"
                    out_path = raw_dir / file_name
                    with open(out_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        writer.writerows(data_rows)
                    print(f"Saved {file_name} with {len(data_rows)} rows")
                else:
                    print(f"No data table for {year} {cat_name}")
            else:
                print(f"Failed to load {year} {cat_name}: status {response.status_code}")


if __name__ == "__main__":
    main()
