#!/usr/bin/env python3
"""Camp Desk SoT flags → daily-intel proposed queue → accept (one depth pack).

Extends ``is_material_depth`` / daily intel / rematerialize — no second SoT,
no public UI.

Usage:
  # List open / overdue material flags (+ draft override count)
  python scripts/nfl/queue_camp_sot_flags.py --scan

  # Write proposals under data/ops/nfl-daily-intel/proposed/
  python scripts/nfl/queue_camp_sot_flags.py --queue
  python scripts/nfl/queue_camp_sot_flags.py --queue --only-overdue

  # Human reviews proposal, fills overrides if needed, then:
  python scripts/nfl/queue_camp_sot_flags.py --accept path.json
  python scripts/nfl/queue_camp_sot_flags.py --accept path.json --write
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

from src.services.nfl_camp_sot_queue import (  # noqa: E402
    DEFAULT_OVERDUE_HOURS,
    accept_proposal,
    overdue_summary,
    queue_flags,
    scan_camp_sot_flags,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Print open/overdue SoT flags")
    ap.add_argument("--queue", action="store_true", help="Write proposal JSON files")
    ap.add_argument(
        "--accept",
        type=Path,
        help="Accept a proposal (writes pending/; optional --write pack)",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="With --accept: apply overrides to the depth SoT pack",
    )
    ap.add_argument(
        "--allow-empty",
        action="store_true",
        help="With --accept: mark flag reviewed with zero overrides",
    )
    ap.add_argument("--only-overdue", action="store_true", help="Queue overdue only")
    ap.add_argument(
        "--only-with-drafts",
        action="store_true",
        help="Queue only flags that have draft overrides",
    )
    ap.add_argument(
        "--overdue-hours",
        type=int,
        default=DEFAULT_OVERDUE_HOURS,
        help=f"Hours after desk_date before overdue (default {DEFAULT_OVERDUE_HOURS})",
    )
    ap.add_argument(
        "--all-dates",
        action="store_true",
        help="Scan every Camp Desk day file (default: newest desk_date only)",
    )
    ap.add_argument("--json", action="store_true", help="Machine-readable scan output")
    args = ap.parse_args()

    if not (args.scan or args.queue or args.accept):
        ap.error("pass --scan, --queue, and/or --accept")

    if args.accept:
        result = accept_proposal(
            args.accept,
            write_pack=args.write,
            allow_empty_overrides=args.allow_empty,
        )
        print(json.dumps(result, indent=2))
        if result.get("rematerialize_hint"):
            print(result["rematerialize_hint"])
        return 0

    flags = scan_camp_sot_flags(
        overdue_hours=args.overdue_hours,
        latest_desk_only=not args.all_dates,
    )
    summary = overdue_summary(flags)

    if args.scan:
        if args.json:
            print(
                json.dumps(
                    {"summary": summary, "flags": [f.as_dict() for f in flags]},
                    indent=2,
                )
            )
        else:
            print(
                f"material={summary['total_material']} open={summary['open']} "
                f"queued={summary['queued']} overdue={summary['overdue']} "
                f"draft_overrides={summary['draft_override_count']}"
            )
            for flag in flags:
                mark = "OVERDUE" if flag.overdue else flag.status.upper()
                drafts = len(flag.draft_overrides)
                print(
                    f"  [{mark}] {flag.flag_id}  drafts={drafts}  "
                    f"age_h={flag.age_hours:.0f}"
                )
                if flag.sot_flag:
                    print(f"           {flag.sot_flag[:120]}")

    if args.queue:
        written = queue_flags(
            flags,
            only_overdue=args.only_overdue,
            only_with_drafts=args.only_with_drafts,
        )
        print(f"queued {len(written)} proposal(s)")
        for path in written:
            print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
