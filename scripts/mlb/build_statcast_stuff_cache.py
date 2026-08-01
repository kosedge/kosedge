#!/usr/bin/env python3
"""Prewarm Baseball Savant pitch CSV cache for stuff_proxy densify.

Usage (from repo root, with model-service on PYTHONPATH):
  cd services/model-service && python ../../scripts/mlb/build_statcast_stuff_cache.py \\
      --season 2026 --start 2026-03-20 --end 2026-07-16

Caches under data/mlb/statcast_cache/ (gitignored). No Odds API credits.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.mlb_statcast_stuff import (  # noqa: E402
    CACHE_DIR,
    ensure_statcast_pitches_through,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--start", type=str, default="2026-03-20")
    p.add_argument("--end", type=str, default="2026-07-16")
    args = p.parse_args()
    end = date.fromisoformat(args.end)
    print(f"Building Statcast stuff cache → {CACHE_DIR} through {end.isoformat()}")
    ensure_statcast_pitches_through(season=int(args.season), through=end)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
