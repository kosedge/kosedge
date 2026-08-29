#!/usr/bin/env python3
"""DepthSotWorkItem gated workflow: queue → accept/reject → remat receipt.

Notes stay copy. Proposals never auto-apply. Accept is the only pack/remat gate.
Remat fail ≠ accepted (pack rolled back). No public UI.

Queue files: data/ops/nfl-daily-intel/queue/runtime/ (gitignored).

Usage:
  python scripts/nfl/queue_camp_sot_flags.py --scan
  python scripts/nfl/queue_camp_sot_flags.py --queue
  python scripts/nfl/queue_camp_sot_flags.py --scan-defense
  python scripts/nfl/queue_camp_sot_flags.py --queue-defense
  python scripts/nfl/queue_camp_sot_flags.py --scan-report
  python scripts/nfl/queue_camp_sot_flags.py --queue-report
  python scripts/nfl/queue_camp_sot_flags.py --alert-t1
  python scripts/nfl/queue_camp_sot_flags.py --accept path.json --dry-run
  python scripts/nfl/queue_camp_sot_flags.py --accept path.json --write --rematerialize --actor desk
  python scripts/nfl/queue_camp_sot_flags.py --reject path.json --actor desk --reason 'thin'
  python scripts/nfl/queue_camp_sot_flags.py --no-change path.json --actor desk
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
    close_work_item,
    live_remat_fn,
    overdue_summary,
    queue_flags,
    scan_camp_sot_flags,
    t1_past_kei_publish,
)
from src.services.nfl_defense_sot_populate import (  # noqa: E402
    format_populate_table,
    queue_defense_flags,
    scan_defense_populate,
)
from src.services.nfl_injury_report_scan import (  # noqa: E402
    REPORT_SOURCE,
    format_t1_table,
    queue_injury_report_flags,
    scan_injury_report,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Print open/overdue DepthSotWorkItems")
    ap.add_argument("--queue", action="store_true", help="Upsert work items into queue/runtime/")
    ap.add_argument(
        "--scan-defense",
        action="store_true",
        help="Print defense populate table (IR/out + named starters vs pack); no accepts",
    )
    ap.add_argument(
        "--queue-defense",
        action="store_true",
        help="Upsert defense populate T1s into queue/runtime/ (propose only; no accepts)",
    )
    ap.add_argument(
        "--scan-report",
        action="store_true",
        help="Week-of injury report T1s (Sleeper DNP/LP/FP/Out); propose only",
    )
    ap.add_argument(
        "--queue-report",
        action="store_true",
        help="Upsert injury-report T1s into queue/runtime/ (propose only; no accepts)",
    )
    ap.add_argument(
        "--alert-t1",
        action="store_true",
        help="Exit 1 if any T1 is still open past next KEI publish (camp + report)",
    )
    ap.add_argument("--accept", type=Path, help="Accept a work item")
    ap.add_argument("--reject", type=Path, help="Reject — write nothing, no remat")
    ap.add_argument(
        "--no-change",
        type=Path,
        dest="no_change",
        help="Close as no_change — write nothing, no remat",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="With --accept: preview pack_diff/line_delta; write nothing; leave queue open",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="With --accept: apply structured overrides to the one depth pack",
    )
    ap.add_argument(
        "--rematerialize",
        action="store_true",
        help="With --accept --write: run remat gate (fail ⇒ not accepted, pack rolled back)",
    )
    ap.add_argument(
        "--allow-empty",
        action="store_true",
        help="With --accept: T3 Pass / reviewed with zero overrides",
    )
    ap.add_argument("--actor", default="cli", help="Audit actor (staff id / desk)")
    ap.add_argument("--reason", default="", help="Audit reason")
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
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    args = ap.parse_args()

    actions = [
        args.scan,
        args.queue,
        args.scan_defense,
        args.queue_defense,
        args.scan_report,
        args.queue_report,
        args.alert_t1,
        args.accept,
        args.reject,
        args.no_change,
    ]
    if not any(actions):
        ap.error(
            "pass --scan, --queue, --scan-defense, --queue-defense, "
            "--scan-report, --queue-report, "
            "--alert-t1, --accept, --reject, and/or --no-change"
        )

    if NOTES_MAY_TOUCH_MEANS or PROPOSALS_MAY_AUTO_APPLY:
        print("FATAL: notes/proposals must not auto-write lines", file=sys.stderr)
        return 2

    if args.reject:
        print(
            json.dumps(
                close_work_item(
                    args.reject,
                    disposition="reject",
                    reason=args.reason,
                    actor=args.actor,
                ),
                indent=2,
            )
        )
        return 0
    if args.no_change:
        print(
            json.dumps(
                close_work_item(
                    args.no_change,
                    disposition="no_change",
                    reason=args.reason,
                    actor=args.actor,
                ),
                indent=2,
            )
        )
        return 0

    if args.accept:
        if args.dry_run and args.write:
            ap.error("--dry-run cannot combine with --write")
        try:
            result = accept_proposal(
                args.accept,
                write_pack=args.write,
                rematerialize=args.rematerialize,
                remat_fn=live_remat_fn() if (args.rematerialize and not args.dry_run) else None,
                allow_empty_overrides=args.allow_empty,
                actor=args.actor,
                reason=args.reason,
                dry_run=args.dry_run,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2))
        if result.get("disposition") == "dry_run":
            print("DRY-RUN — pack/queue untouched", file=sys.stderr)
            return 0
        if result.get("disposition") == "remat_failed":
            print("REMAT FAILED — pack rolled back; not accepted", file=sys.stderr)
            return 3
        rid = str(result.get("remat_run_id") or "")
        if args.rematerialize and rid.startswith("receipt-only-"):
            print(
                "WARNING: remat_run_id is still receipt-only — live remat hook not on prod",
                file=sys.stderr,
            )
            return 4
        if result.get("rematerialize_hint"):
            print("REMAT:", result["rematerialize_hint"])
        return 0

    if args.scan_defense or args.queue_defense:
        flags, table = scan_defense_populate()
        print(format_populate_table(table))
        print()
        proposed = [r for r in table if r.proposed_t1]
        print(
            f"proposed_t1={len(proposed)} queued_candidates={len(flags)} "
            f"(STOP for human accept — zero accepts in this path)"
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "table": [r.as_dict() for r in table],
                        "work_item_ids": [f.work_item_id for f in flags],
                        "accepts_performed": 0,
                    },
                    indent=2,
                )
            )
        if args.queue_defense:
            q = queue_defense_flags(flags)
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

    if args.scan_report or args.queue_report:
        items, rows, meta = scan_injury_report()
        print(format_t1_table(rows))
        print()
        print(
            f"injury_report t1={len(rows)} source={meta.get('source')} "
            f"as_of={meta.get('as_of')} (STOP — zero accepts)"
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "meta": meta,
                        "t1": [r.as_dict() for r in rows],
                        "work_item_ids": [f.work_item_id for f in items],
                        "accepts_performed": 0,
                        "source": REPORT_SOURCE,
                    },
                    indent=2,
                )
            )
        if args.queue_report:
            q = queue_injury_report_flags(items)
            print(
                json.dumps(
                    {
                        "created": [str(p) for p in q.created],
                        "updated": [str(p) for p in q.updated],
                        "unchanged": [str(p) for p in q.unchanged],
                        "skipped": q.skipped,
                        "accepts_performed": 0,
                        "source": REPORT_SOURCE,
                    },
                    indent=2,
                )
            )
        return 0

    flags = scan_camp_sot_flags(
        overdue_hours=args.overdue_hours,
        latest_desk_only=not args.all_dates,
    )
    summary = overdue_summary(flags)

    if args.alert_t1:
        report_items, _, _ = scan_injury_report()
        all_for_alert = list(flags) + list(report_items)
        alerts = t1_past_kei_publish(all_for_alert)
        payload = {
            "alert": "t1_past_kei_publish",
            "count": len(alerts),
            "work_item_ids": [f.work_item_id for f in alerts],
            "teams": [f.team for f in alerts],
            "sources": sorted(
                {
                    (
                        "sleeper"
                        if "injury-report" in f.work_item_id
                        else "camp_desk"
                    )
                    for f in alerts
                }
            ),
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            src = ",".join(payload["sources"]) or "none"
            print(
                f"T1 past KEI publish: {len(alerts)} "
                f"teams={','.join(f.team for f in alerts) or 'none'} "
                f"sources={src}"
            )
        return 1 if alerts else 0

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
                f"t1_past_kei={summary['t1_past_kei_publish_count']} "
                f"proposed_patch_rows={summary['draft_override_count']}"
            )
            print(
                "contract: notes≠means; patch≠auto; accept-only remat; "
                "remat-fail≠accepted; no public UI; queue≠remat"
            )
            for flag in flags:
                mark = "OVERDUE" if flag.overdue else flag.status.upper()
                drafts = len(flag.proposed_patch)
                why = f" ({flag.overdue_reason})" if flag.overdue_reason else ""
                print(
                    f"  [{mark}] [{flag.tier}] {flag.team}  "
                    f"patch={drafts}  sla_h={flag.sla_hours}  "
                    f"kei={flag.next_kei_publish}  age_h={flag.age_hours:.0f}{why}"
                )
                if flag.sot_flag:
                    print(f"           {flag.sot_flag[:120]}")

    if args.queue:
        result = queue_flags(
            flags,
            only_overdue=args.only_overdue,
            only_with_drafts=args.only_with_drafts,
            tiers=args.tier,
        )
        if args.json:
            print(json.dumps(result.as_dict(), indent=2))
        else:
            print(
                f"queue idempotent: created={len(result.created)} "
                f"updated={len(result.updated)} unchanged={len(result.unchanged)} "
                f"skipped={len(result.skipped)}"
            )
            for path in result.written:
                print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
