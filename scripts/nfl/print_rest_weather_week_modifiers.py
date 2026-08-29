#!/usr/bin/env python3
"""Print Week N cards that would get a rest or weather modifier. No accepts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--no-weather",
        action="store_true",
        help="Skip Open-Meteo/NWS fetch (rest/TZ only)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="",
        help="Override gitignored weather cache dir",
    )
    args = parser.parse_args()

    from src.services.nfl_rest_weather_feed import print_week_rest_weather_modifiers

    cache = Path(args.cache_dir) if args.cache_dir else None
    print_week_rest_weather_modifiers(
        week=args.week,
        season=args.season,
        fetch_weather=not args.no_weather,
        cache_dir=cache,
    )
    print("STOP — no accepts (source feed only).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
