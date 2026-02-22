"""
Fetch NCAAB game results from ESPN's scoreboard API (no auth required).
Use this for seasons where Sports-Reference returns 404 (e.g. 2022+).

Writes one CSV per season to data/raw/games/ as espn_cbb_games_{yr}.csv with columns
Date, Visitor, PTS, Home, PTS_2 so build_actual_margins.py can match to odds.

API: https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=YYYYMMDD

Run from apps/web: python scrape_cbb_results_espn.py
"""
import csv
import time
from datetime import date, timedelta
from pathlib import Path

import requests

# Same raw dir as other scrapers and build_actual_margins
import sys
_WEB = Path(__file__).resolve().parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_GAMES, ensure_dirs
ensure_dirs()
RAW_DIR = RAW_GAMES

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

# Season end years to fetch (2022 = 2021-22, etc.). Use when Sports-Reference 404s.
# Include current season (e.g. 2026 = 2025-26) so backtest can have "this season" results.
YEARS = (2022, 2023, 2024, 2025, 2026)

# NCAAB season: early Nov (year-1) through early Apr (year)
SEASON_START_MONTH = 11
SEASON_START_DAY = 1
SEASON_END_MONTH = 4
SEASON_END_DAY = 10

DELAY_SECONDS = 0.5  # Polite rate limit


def season_date_range(end_year: int):
    """Yield (start_date, end_date) for the season ending in end_year."""
    start = date(end_year - 1, SEASON_START_MONTH, SEASON_START_DAY)
    end = date(end_year, SEASON_END_MONTH, SEASON_END_DAY)
    return start, end


def fetch_day(game_date: date) -> list[dict]:
    """Return list of {date_str, visitor, home, away_pts, home_pts} for completed games."""
    dt_str = game_date.strftime("%Y%m%d")
    url = f"{BASE_URL}?dates={dt_str}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  Error {game_date}: {e}")
        return []

    events = data.get("events") or []
    rows = []
    for ev in events:
        status = ev.get("status") or {}
        stype = status.get("type") or {}
        if stype.get("state") != "post" or not stype.get("completed"):
            continue
        comps = (ev.get("competitions") or [{}])[0]
        competitors = comps.get("competitors") or []
        if len(competitors) != 2:
            continue
        home = next((c for c in competitors if (c.get("homeAway") or "").lower() == "home"), None)
        away = next((c for c in competitors if (c.get("homeAway") or "").lower() == "away"), None)
        if not home or not away:
            continue
        try:
            home_pts = int(home.get("score") or 0)
            away_pts = int(away.get("score") or 0)
        except (TypeError, ValueError):
            continue
        team = lambda c: (c.get("team") or {}).get("shortDisplayName") or (c.get("team") or {}).get("displayName") or ""
        rows.append({
            "Date": game_date.strftime("%Y-%m-%d"),
            "Visitor": team(away),
            "PTS": away_pts,
            "Home": team(home),
            "PTS_2": home_pts,
        })
    return rows


def main() -> None:
    for yr in YEARS:
        start_d, end_d = season_date_range(yr)
        print(f"Fetching {yr} season ({start_d} to {end_d})...")
        all_rows = []
        current = start_d
        while current <= end_d:
            rows = fetch_day(current)
            all_rows.extend(rows)
            current += timedelta(days=1)
            time.sleep(DELAY_SECONDS)

        if not all_rows:
            print(f"  No games found for {yr}")
            continue

        # Write CSV (same column semantics as Sports-Reference for build_actual_margins)
        out_path = RAW_DIR / f"espn_cbb_games_{yr}.csv"
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Visitor", "PTS", "Home", "PTS_2"])
            for r in all_rows:
                w.writerow([r["Date"], r["Visitor"], r["PTS"], r["Home"], r["PTS_2"]])
        print(f"Success! Saved {len(all_rows)} games to {out_path}")

    print("Done. Run: python src/build_actual_margins.py to match to odds.")


if __name__ == "__main__":
    main()
