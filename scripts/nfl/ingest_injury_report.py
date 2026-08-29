#!/usr/bin/env python3
"""Week-of injury report ingest (Sleeper) → DepthSot T1 propose-only.

Usage:
  python scripts/nfl/ingest_injury_report.py --scan
  python scripts/nfl/ingest_injury_report.py --queue
  python scripts/nfl/ingest_injury_report.py --scan --force-refresh

T1 only if starter or snap_share_prior >= 0.40 AND (Out/IR or 2× DNP)
AND pack still full-go. No auto-accept. Print T1 list and stop.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MS = REPO / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_injury_report_scan import (  # noqa: E402
    format_t1_table,
    queue_injury_report_flags,
    scan_injury_report,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Print T1 candidates (no accepts)")
    ap.add_argument("--queue", action="store_true", help="Upsert T1s into queue/runtime/")
    ap.add_argument("--force-refresh", action="store_true", help="Bypass Sleeper cache TTL")
    ap.add_argument("--as-of", default="", help="as_of date YYYY-MM-DD (default: UTC today)")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    args = ap.parse_args()
    if not args.scan and not args.queue:
        ap.error("pass --scan and/or --queue")

    items, rows, meta = scan_injury_report(
        as_of=args.as_of or None,
        force_refresh=args.force_refresh,
    )
    print(format_t1_table(rows))
    print()
    print(
        f"t1_count={len(rows)} work_items={len(items)} "
        f"source={meta.get('source')} as_of={meta.get('as_of')} "
        f"(STOP — zero accepts)"
    )
    if args.json:
        print(
            json.dumps(
                {
                    "meta": meta,
                    "t1": [r.as_dict() for r in rows],
                    "work_item_ids": [f.work_item_id for f in items],
                    "accepts_performed": 0,
                },
                indent=2,
            )
        )
    if args.queue:
        q = queue_injury_report_flags(items)
        print(
            json.dumps(
                {
                    "created": [str(p) for p in q.created],
                    "updated": [str(p) for p in q.updated],
                    "unchanged": [str(p) for p in q.unchanged],
                    "skipped": q.skipped,
                    "accepts_performed": 0,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
