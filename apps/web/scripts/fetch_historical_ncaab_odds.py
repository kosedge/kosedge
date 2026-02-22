#!/usr/bin/env python3
"""
Fetch NCAAB historical odds (open + close) from The Odds API and save to
data/raw/odds/open/ and data/raw/odds/close/.

Uses ODDS_API_KEY from environment. Historical data is only available from
2020-11-16 for NCAAB. Cost: 20 credits per request (regions=us, markets=spreads,totals);
we do 2 requests per day = 40 credits/day.

Usage (from apps/web):
  export ODDS_API_KEY="your_key"
  python scripts/fetch_historical_ncaab_odds.py
  python scripts/fetch_historical_ncaab_odds.py --start 2024-11-01 --end 2025-02-15
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE_URL = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
# NCAAB historical data starts 2020-11-16 per Odds API docs
DEFAULT_START = "2020-11-16"
CREDITS_PER_REQUEST = 20  # regions=us (1) * markets=spreads,totals (2) * 10 = 20


def parse_args():
    p = argparse.ArgumentParser(description="Fetch NCAAB historical odds (open + close)")
    p.add_argument("--start", default=DEFAULT_START, help=f"Start date YYYY-MM-DD (default {DEFAULT_START})")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD (default today)")
    p.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (default 1)")
    p.add_argument("--dry-run", action="store_true", help="Print requests only, do not fetch")
    return p.parse_args()


def fetch_snapshot(api_key: str, dt: datetime) -> tuple[dict | None, int, str | None]:
    """Fetch one historical snapshot at dt (UTC). Returns (response_json, credits_used, error_msg or None)."""
    iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "regions": "us",
        "markets": "spreads,totals",
        "oddsFormat": "american",
        "apiKey": api_key,
        "date": iso,
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
    except requests.RequestException as e:
        return None, 0, str(e)[:80]
    credits = int(r.headers.get("x-requests-last", CREDITS_PER_REQUEST))
    if r.status_code != 200:
        try:
            body = (r.json() or {}).get("message", r.text[:100] if r.text else "")
        except Exception:
            body = r.text[:100] if r.text else ""
        err = f"{r.status_code} {r.reason or ''}".strip()
        if body:
            err += f" — {body}"
        return None, credits, err[:120]
    return r.json(), credits, None


def _load_dotenv():
    """Load .env.local or .env from apps/web so ODDS_API_KEY is set if not in env."""
    if os.environ.get("ODDS_API_KEY"):
        return
    root = Path(__file__).resolve().parent.parent
    for name in (".env.local", ".env"):
        path = root / name
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line and line.split("=", 1)[0].strip() == "ODDS_API_KEY":
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    if value:
                        os.environ["ODDS_API_KEY"] = value
                    return


def main():
    _load_dotenv()
    args = parse_args()
    api_key = (os.environ.get("ODDS_API_KEY") or "").strip()
    if not api_key:
        print("Set ODDS_API_KEY in the environment or in apps/web/.env.local")
        return 1

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else datetime.utcnow().date()
    if start > end:
        print("Start must be <= end.")
        return 1

    root = Path(__file__).resolve().parent.parent
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from pipeline_paths import ODDS_OPEN, ODDS_CLOSE, ensure_dirs
    ensure_dirs()
    open_dir = ODDS_OPEN
    close_dir = ODDS_CLOSE

    total_credits = 0
    days = (end - start).days + 1
    estimated_credits = days * 2 * CREDITS_PER_REQUEST
    print(f"Date range: {start} to {end} ({days} days). Estimated credits: {estimated_credits} (20 per request, 2 per day).")

    if args.dry_run:
        print("Dry run: would request open + close for each day.")
        return 0

    for i in range(days):
        d = start + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        # Open: 12:00 UTC that day; close: 22:00 UTC that day
        open_ts = datetime(d.year, d.month, d.day, 12, 0, 0)
        close_ts = datetime(d.year, d.month, d.day, 22, 0, 0)

        for label, ts, out_dir in [("open", open_ts, open_dir), ("close", close_ts, close_dir)]:
            out_file = out_dir / f"{date_str}.json"
            if out_file.exists():
                print(f"  Skip {date_str} {label} (exists)")
                continue
            data, used, err = fetch_snapshot(api_key, ts)
            total_credits += used
            if data is None:
                print(f"  Fail {date_str} {label}" + (f" ({err})" if err else ""))
                continue
            with open(out_file, "w") as f:
                json.dump(data, f, indent=2)
            n_events = len(data.get("data", []))
            print(f"  {date_str} {label}: {n_events} events -> {out_file.name}")
            time.sleep(args.delay)

    print(f"Done. Total credits used this run: ~{total_credits} (check API dashboard for exact).")
    return 0


if __name__ == "__main__":
    exit(main())
