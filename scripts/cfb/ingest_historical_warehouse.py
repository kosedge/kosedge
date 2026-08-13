#!/usr/bin/env python3
"""Download-once CFB historical warehouse ingest (SportsDataverse → HD parquet).

Usage:
  python scripts/cfb/ingest_historical_warehouse.py
  python scripts/cfb/ingest_historical_warehouse.py --seasons 2022,2023,2024,2025
  python scripts/cfb/ingest_historical_warehouse.py --repo-fallback   # no HD
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.ingest import DEFAULT_SEASONS, run_ingest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seasons",
        default=",".join(str(y) for y in DEFAULT_SEASONS),
        help="Comma-separated seasons (default 2020-2025)",
    )
    parser.add_argument(
        "--repo-fallback",
        action="store_true",
        help="Write under data/cfb/warehouse even if HD is mounted",
    )
    parser.add_argument("--skip-odds", action="store_true", help="Skip Odds API lake overlay")
    parser.add_argument("--skip-pbp", action="store_true", help="Skip cfbfastR PBP download")
    parser.add_argument(
        "--pbp-seasons",
        default="2014-2025",
        help="PBP seasons as start-end or comma list (default 2014-2025)",
    )
    args = parser.parse_args(argv)
    seasons = [int(s.strip()) for s in args.seasons.split(",") if s.strip()]
    pbp_seasons = None
    if not args.skip_pbp:
        raw = args.pbp_seasons.strip()
        if "-" in raw and "," not in raw:
            a, b = raw.split("-", 1)
            pbp_seasons = list(range(int(a), int(b) + 1))
        else:
            pbp_seasons = [int(s.strip()) for s in raw.split(",") if s.strip()]
    inventory = run_ingest(
        seasons=seasons,
        prefer_hd=not args.repo_fallback,
        ingest_odds=not args.skip_odds,
        ingest_pbp_seasons=pbp_seasons,
    )
    print(json.dumps(inventory, indent=2, default=str))
    return 0 if inventory.get("games") else 1


if __name__ == "__main__":
    raise SystemExit(main())
