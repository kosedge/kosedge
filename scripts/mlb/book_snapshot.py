#!/usr/bin/env python3
"""Generic The Book snapshot stub for non-CFB sports.

Same ledger schema. Sport-specific market/KEI join lands next; CFB is live first.

Usage:
  PYTHONPATH=services/model-service:. \\
    python scripts/nfl/book_snapshot.py --date 2026-09-10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

SPORT = Path(__file__).resolve().parent.name  # nfl|nba|mlb|ncaam|wnba from path


def main() -> int:
    ap = argparse.ArgumentParser(description=f"The Book — {SPORT} slate snapshot")
    ap.add_argument("--date", required=True)
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()
    print(
        f"The Book: sport={SPORT} date={args.date} season={args.season}\n"
        "Schema ready (same book_ledger). Sport join not implemented yet — "
        "CFB is first. See scripts/cfb/book_snapshot.py."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
