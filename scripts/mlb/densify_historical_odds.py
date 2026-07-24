#!/usr/bin/env python3
"""DK-first MLB historical odds densify (open + mid + evening-close passes).

Usage:
  PYTHONPATH=services/model-service \
    python scripts/mlb/densify_historical_odds.py \
      --start-date 2026-05-01 --end-date 2026-07-23 --max-requests 80 --open-pass
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
    ap.add_argument(
        "--open-pass",
        action="store_true",
        help="Also run open densify (day_offset=-1 @ 12:00 and 18:00 UTC)",
    )
    ap.add_argument(
        "--evening-close",
        action="store_true",
        help="Also run evening close densify (day_offset=0 @ 23:00 UTC)",
    )
    args = ap.parse_args()

    # Midday close (legacy default) — often already cached.
    close_result = pull_mlb_historical_odds_densify(
        start_date=args.start_date,
        end_date=args.end_date,
        bookmakers=args.bookmakers,
        max_requests=args.max_requests,
        day_offset=0,
        snapshot_hour_utc=17,
    )
    payload: dict = {"close_midday": close_result}
    statuses = [close_result.get("status")]

    if args.evening_close:
        evening = pull_mlb_historical_odds_densify(
            start_date=args.start_date,
            end_date=args.end_date,
            bookmakers=args.bookmakers,
            max_requests=args.max_requests,
            day_offset=0,
            snapshot_hour_utc=23,
        )
        payload["close_evening"] = evening
        statuses.append(evening.get("status"))

    if args.open_pass:
        for label, hour in (("open_noon", 12), ("open_evening", 18)):
            open_result = pull_mlb_historical_odds_densify(
                start_date=args.start_date,
                end_date=args.end_date,
                bookmakers=args.bookmakers,
                max_requests=args.max_requests,
                day_offset=-1,
                snapshot_hour_utc=hour,
            )
            payload[label] = open_result
            statuses.append(open_result.get("status"))

    print(json.dumps(payload, indent=2, default=str))
    return 0 if all(s in {"ok", "partial", None} for s in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
