"""
Export KEINFL lines (projected spread + O/U) for the shared edge board.
Reads Kosedge fair-lines from the model-service and writes
data/processed/kei_lines_nfl.json with Odds-API team names.

Usage (from repo root or apps/web):
  MODEL_SERVICE_URL=http://127.0.0.1:8000 python apps/web/scripts/export_kei_lines_nfl.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
OUT = WEB / "data" / "processed" / "kei_lines_nfl.json"


def main() -> int:
    base = (os.environ.get("MODEL_SERVICE_URL") or "http://127.0.0.1:8000").rstrip("/")
    season = int(os.environ.get("NFL_KEI_SEASON") or "2026")
    days_ahead = int(os.environ.get("NFL_KEI_DAYS_AHEAD") or "200")
    include_past = int(os.environ.get("NFL_KEI_INCLUDE_PAST_DAYS") or "14")
    url = (
        f"{base}/nfl/fair-lines"
        f"?season={season}&days_ahead={days_ahead}&include_past_days={include_past}"
    )

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Failed to fetch fair-lines from {url}: {exc}", file=sys.stderr)
        return 1

    lines = payload.get("lines") or []
    games = []
    for row in lines:
        home = (row.get("home_team") or "").strip()
        away = (row.get("away_team") or "").strip()
        if not home or not away:
            continue
        spread = row.get("spread_home")
        total = row.get("total_mean")
        commence = row.get("start_time") or row.get("game_date")
        games.append(
            {
                "id": row.get("game_id"),
                "homeTeam": home,
                "awayTeam": away,
                "homeAbbr": row.get("home_abbr"),
                "awayAbbr": row.get("away_abbr"),
                "commenceTime": commence,
                "projSpreadHome": round(float(spread), 2) if spread is not None else None,
                "projTotal": round(float(total), 2) if total is not None else None,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"sport": "nfl", "keiCode": "KEINFL", "games": games}, f, indent=2)
        f.write("\n")

    print(f"Wrote {OUT} with {len(games)} games (KEINFL).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
