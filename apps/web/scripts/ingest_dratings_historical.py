"""
Fetch historical D-Ratings seasons via browser automation and save CSVs.
Run from apps/web: python scripts/ingest_dratings_historical.py
Requires: pip install playwright && playwright install chromium

Uses Playwright to open the ratings page, select each season from the dropdown,
scrape the table, and save data/raw/ratings/dratings_ratings_YYYY.csv for
season-end years 2020–2025 (2026 is from ingest_dratings.py).
"""
import csv
import re
import sys
from pathlib import Path

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_RATINGS, ensure_dirs

ensure_dirs()

URL = "https://www.dratings.com/sports/ncaa-college-basketball-ratings/"

# Season dropdown: label like "2024-2025" -> season-end year 2025
# We fetch 2020 through 2025 (2026 is current, use ingest_dratings.py)
HISTORICAL_SEASONS = [
    ("2024-2025", 2025),
    ("2023-2024", 2024),
    ("2022-2023", 2023),
    ("2021-2022", 2022),
    ("2020-2021", 2021),
    ("2019-2020", 2020),
]


def _team_from_cell(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    s = re.sub(r"^\d+\.\s*", "", s)
    s = re.sub(r"\s*\(\d+-\d+\)\s*$", "", s).strip()
    return s


def _parse_table(html: str) -> list[dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue
        raw_first = (cells[0].get_text() or "").strip()
        team = _team_from_cell(raw_first)
        if not team:
            continue
        raw_second = (cells[1].get_text() or "").strip().replace(",", "")
        try:
            rating = float(raw_second)
        except ValueError:
            continue
        rows.append({"team": team, "dratings_rating": rating})
    return rows


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(URL, wait_until="networkidle", timeout=20000)
        page.wait_for_selector("table", timeout=10000)

        for label, year in HISTORICAL_SEASONS:
            try:
                selected = False
                # Strategy 1: native <select> by label (e.g. "2024-2025")
                if page.locator("select").count() > 0:
                    try:
                        page.locator("select").first.select_option(label=label)
                        selected = True
                    except Exception:
                        pass
                # Strategy 2: select by value
                if not selected and page.locator("select").count() > 0:
                    for val in [label, str(year)]:
                        try:
                            page.locator("select").first.select_option(value=val)
                            selected = True
                            break
                        except Exception:
                            continue
                # Strategy 3: click element with season text (custom dropdown)
                if not selected:
                    try:
                        page.get_by_text(label, exact=True).first.click(timeout=3000)
                        selected = True
                    except Exception:
                        pass
                if not selected:
                    try:
                        opt = page.locator(f"text={label}").first
                        if opt.count() > 0:
                            opt.click(timeout=3000)
                            selected = True
                    except Exception:
                        pass
                if not selected:
                    print(f"  {year}: could not select season {label}, skipping")
                    continue
                # Wait for table to settle (selection may trigger navigation or JS update)
                page.wait_for_timeout(2500)
                html = None
                for attempt in range(4):
                    try:
                        page.wait_for_load_state("networkidle", timeout=6000)
                        page.wait_for_timeout(600)
                        html = page.content()
                        break
                    except Exception as e1:
                        page.wait_for_timeout(2000)
                        if attempt == 3:
                            print(f"  {year}: page content failed ({e1}), skipping")
                            break
                if html is None:
                    continue
                data = _parse_table(html)
                if not data:
                    print(f"  {year}: no table data for {label}, skipping")
                    continue
                out_path = RAW_RATINGS / f"dratings_ratings_{year}.csv"
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=["team", "dratings_rating"])
                    w.writeheader()
                    w.writerows(data)
                print(f"  Saved dratings_ratings_{year}.csv ({len(data)} rows) for {label}")
            except Exception as e:
                print(f"  {year} ({label}): {e}")
        browser.close()

    print("Done. Run ingest_dratings.py for current season (2026) if needed.")


if __name__ == "__main__":
    main()
