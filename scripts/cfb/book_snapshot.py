#!/usr/bin/env python3
"""Snapshot today's CFB slate into The Book (pending).

Freezes KEI + market at post. Does not grade. Primary metric is CLV (later).

Usage:
  PYTHONPATH=services/model-service:. \\
    python scripts/cfb/book_snapshot.py --date 2026-08-29

  # include MEM@UNLV (tips 08-30 02:00Z) on the Aug 29 desk window
  PYTHONPATH=services/model-service:. \\
    python scripts/cfb/book_snapshot.py --date 2026-08-29 --include-aug30-late
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.book_ledger.cfb_snapshot import snapshot_cfb_slate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="The Book — CFB slate snapshot")
    ap.add_argument("--date", required=True, help="Slate date YYYY-MM-DD")
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--stake-flag", default="paper", choices=["paper", "booked"])
    ap.add_argument("--actor", default="book_snapshot")
    ap.add_argument(
        "--include-aug30-late",
        action="store_true",
        help="Include 2026-08-30 early games (MEM@UNLV) with Aug 29 slate",
    )
    ap.add_argument("--json", action="store_true", help="Print full JSON artifact")
    args = ap.parse_args()

    artifact = snapshot_cfb_slate(
        slate_date=args.date,
        season=args.season,
        actor=args.actor,
        stake_flag=args.stake_flag,
        include_aug30_late=args.include_aug30_late,
    )
    c = artifact.get("counts") or {}
    print("=== The Book — CFB snapshot ===")
    print(f"slate_date: {artifact.get('slate_date')}")
    print(f"posted_at:  {artifact.get('posted_at')}")
    print(f"games:      {c.get('games')}")
    print(f"play:       {c.get('play')}")
    print(f"lean:       {c.get('lean')}")
    print(f"pass:       {c.get('pass')}")
    print(f"late_post:  {c.get('late_post')}")
    print(f"created:    {c.get('created')}  reused: {c.get('reused')}")
    print(f"artifact:   {artifact.get('artifact_path')}")
    print("result:     pending (no fake grades)")
    print("STOP for operator review.")
    if args.json:
        print(json.dumps(artifact, indent=2, default=str))
    else:
        for g in artifact.get("games") or []:
            late = " LATE" if g.get("late_post") else ""
            print(
                f"  {g.get('away')}@{g.get('home')}  type={g.get('type')}  "
                f"kei={g.get('kei_spread_home')}  mkt={g.get('market_spread_home')}  "
                f"edge={g.get('edge_pts')}  trust={g.get('trust_reason')}{late}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
