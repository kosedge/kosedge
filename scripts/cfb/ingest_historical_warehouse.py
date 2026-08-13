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
    args = parser.parse_args(argv)
    seasons = [int(s.strip()) for s in args.seasons.split(",") if s.strip()]
    inventory = run_ingest(seasons=seasons, prefer_hd=not args.repo_fallback)
    print(json.dumps(inventory, indent=2, default=str))
    return 0 if inventory.get("games") else 1


if __name__ == "__main__":
    raise SystemExit(main())
