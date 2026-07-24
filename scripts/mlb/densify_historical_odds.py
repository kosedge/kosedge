#!/usr/bin/env python3
"""DK-first MLB historical odds densify (open + close passes).

Usage:
  PYTHONPATH=services/model-service \
    python scripts/mlb/densify_historical_odds.py \
      --start-date 2025-04-01 --end-date 2025-06-30 --max-requests 60
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.tasks import pull_mlb_historical_odds_densify  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="MLB DK-first historical odds densify")
    ap.add_argument("--start-date", default=None)
    ap.add_argument("--end-date", default=None)
    ap.add_argument("--max-requests", type=int, default=40)
    ap.add_argument("--bookmakers", default="draftkings,fanduel")
    ap.add_argument("--open-pass", action="store_true", help="Also run open densify (day_offset=-1, 18:00 UTC)")
    args = ap.parse_args()

    close_result = pull_mlb_historical_odds_densify(
        start_date=args.start_date,
        end_date=args.end_date,
        bookmakers=args.bookmakers,
        max_requests=args.max_requests,
        day_offset=0,
        snapshot_hour_utc=17,
    )
    payload = {"close": close_result}
    if args.open_pass:
        payload["open"] = pull_mlb_historical_odds_densify(
            start_date=args.start_date,
            end_date=args.end_date,
            bookmakers=args.bookmakers,
            max_requests=args.max_requests,
            day_offset=-1,
            snapshot_hour_utc=18,
        )
    print(json.dumps(payload, indent=2, default=str))
    return 0 if close_result.get("status") in {"ok", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
