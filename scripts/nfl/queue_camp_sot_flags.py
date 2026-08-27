#!/usr/bin/env python3
"""DepthSotWorkItem handoff: Camp Desk SOT FLAG → queue → accept → remat receipt.

Notes stay copy. Proposals never auto-apply. Accept is the only pack/remat gate.
No second SoT. No public UI required.

Usage:
  python scripts/nfl/queue_camp_sot_flags.py --scan
  python scripts/nfl/queue_camp_sot_flags.py --queue
  python scripts/nfl/queue_camp_sot_flags.py --queue --tier T1
  python scripts/nfl/queue_camp_sot_flags.py --accept path.json --write
  # After --write: rematerialize via safe rebuild (receipt records the command)
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
    NOTES_MAY_TOUCH_MEANS,
    PROPOSALS_MAY_AUTO_APPLY,
    accept_proposal,
    overdue_summary,
    queue_flags,
    scan_camp_sot_flags,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Print open/overdue DepthSotWorkItems")
    ap.add_argument("--queue", action="store_true", help="Write work-item JSON to proposed/")
    ap.add_argument(
        "--accept",
        type=Path,
        help="Accept a work item (pending/ + optional --write pack + receipt)",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="With --accept: apply structured overrides to the one depth pack",
    )
    ap.add_argument(
        "--rematerialize",
        action="store_true",
        help="With --accept --write: mark remat required on the receipt (safe weeks 1–18)",
    )
    ap.add_argument(
        "--allow-empty",
        action="store_true",
        help="With --accept: T3 Pass / reviewed with zero overrides",
    )
    ap.add_argument("--only-overdue", action="store_true", help="Queue overdue only")
    ap.add_argument(
        "--only-with-drafts",
        action="store_true",
        help="Queue only items that have a proposed_patch",
    )
    ap.add_argument(
        "--tier",
        action="append",
        choices=["T1", "T2", "T3"],
        help="Queue only these tiers (repeatable)",
    )
    ap.add_argument(
        "--overdue-hours",
        type=int,
        default=None,
        help=f"Override per-tier SLA hours (default T1={DEFAULT_OVERDUE_HOURS})",
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

    if NOTES_MAY_TOUCH_MEANS or PROPOSALS_MAY_AUTO_APPLY:
        print("FATAL: notes/proposals must not auto-write lines", file=sys.stderr)
        return 2

    if args.accept:
        try:
            result = accept_proposal(
                args.accept,
                write_pack=args.write,
                rematerialize=args.rematerialize,
                allow_empty_overrides=args.allow_empty,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2))
        if result.get("rematerialize_hint"):
            print("REMAT:", result["rematerialize_hint"])
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
                    {"summary": summary, "work_items": [f.as_dict() for f in flags]},
                    indent=2,
                )
            )
        else:
            tiers = summary["by_tier"]
            print(
                f"material={summary['total_material']} "
                f"T1={tiers['T1']} T2={tiers['T2']} T3={tiers['T3']} "
                f"open={summary['open']} queued={summary['queued']} "
                f"overdue={summary['overdue']} "
                f"proposed_patch_rows={summary['draft_override_count']}"
            )
            print("contract: notes never touch means/props/spreads; proposals never auto-apply")
            for flag in flags:
                mark = "OVERDUE" if flag.overdue else flag.status.upper()
                drafts = len(flag.proposed_patch)
                print(
                    f"  [{mark}] [{flag.tier}] {flag.work_item_id}  "
                    f"patch={drafts}  sla_h={flag.sla_hours}  age_h={flag.age_hours:.0f}"
                )
                if flag.sot_flag:
                    print(f"           {flag.sot_flag[:120]}")

    if args.queue:
        written = queue_flags(
            flags,
            only_overdue=args.only_overdue,
            only_with_drafts=args.only_with_drafts,
            tiers=args.tier,
        )
        print(f"queued {len(written)} DepthSotWorkItem(s)")
        for path in written:
            print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
