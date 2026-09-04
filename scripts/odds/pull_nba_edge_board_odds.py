#!/usr/bin/env python3
"""Pull live basketball_nba odds → odds_raw_nba.json → edge_board_fallback_nba.json.

Preserves prior Open (first capture); refreshes Best/Current.
Requires ODDS_API_KEY or ODDS_API_KEY_BACKUP (env only — no embedded fallback).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "apps/web/data/processed"
BOOKS = "draftkings,fanduel,betmgm,betrivers,hardrockbet,fanatics,bet365,circa,betr"


def _api_key() -> str:
    for env_name in ("ODDS_API_KEY", "ODDS_API_KEY_BACKUP"):
        key = (os.getenv(env_name) or "").strip()
        if key:
            return key
    raise SystemExit("Set ODDS_API_KEY or ODDS_API_KEY_BACKUP")


def main() -> int:
    key = _api_key()
    qs = urllib.parse.urlencode(
        {
            "apiKey": key,
            "regions": "us",
            "markets": "spreads,totals",
            "oddsFormat": "american",
            "bookmakers": BOOKS,
        }
    )
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?{qs}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        events = json.loads(resp.read().decode("utf-8"))
    if not isinstance(events, list):
        raise SystemExit(f"unexpected odds payload: {type(events)}")

    OUT.mkdir(parents=True, exist_ok=True)
    captured = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_path = OUT / "odds_raw_nba.json"
    raw_path.write_text(
        json.dumps(
            {
                "sport": "nba",
                "source": "odds-api-live-pull",
                "capturedAt": captured,
                "eventCount": len(events),
                "events": events,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {raw_path.name} events={len(events)}")

    # Rebuild fallbacks (nba + any other raw dumps present).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_edge_board_fallbacks import main as build_main

    return build_main()


if __name__ == "__main__":
    raise SystemExit(main())
