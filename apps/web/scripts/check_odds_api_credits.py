#!/usr/bin/env python3
"""
Print Odds API credit usage from response headers.
Uses a single cheap request (sports list) so you can run this often without burning credits.

Response headers (per the-odds-api.com):
  x-requests-remaining  - credits left until quota reset
  x-requests-used       - credits used this period
  x-requests-last       - cost of this request

Run from apps/web: python scripts/check_odds_api_credits.py
Or from repo root: pnpm run check:odds-credits
"""
import os
import sys
from pathlib import Path

import requests

_WEB = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    if os.environ.get("ODDS_API_KEY"):
        return
    for name in (".env.local", ".env"):
        p = _WEB / name
        if not p.is_file():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == "ODDS_API_KEY":
                    os.environ["ODDS_API_KEY"] = v.strip().strip('"').strip("'")
                    return


def main() -> int:
    _load_dotenv()
    key = (os.environ.get("ODDS_API_KEY") or "").strip()
    if not key:
        print("Set ODDS_API_KEY in .env.local or environment.")
        return 1

    # Cheap request: list sports (minimal cost, just to get headers)
    r = requests.get(
        "https://api.the-odds-api.com/v4/sports/",
        params={"apiKey": key},
        timeout=10,
    )
    remaining = r.headers.get("x-requests-remaining")
    used = r.headers.get("x-requests-used")
    last = r.headers.get("x-requests-last")

    print("Odds API credits:")
    print(f"  Remaining: {remaining or '—'}")
    print(f"  Used (this period): {used or '—'}")
    print(f"  Last request cost:  {last or '—'}")
    if r.status_code != 200:
        print(f"  (Response: {r.status_code})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
