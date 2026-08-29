#!/usr/bin/env python3
"""DepthSotWorkItem gated workflow: queue → accept/reject → remat receipt.

Notes stay copy. Proposals never auto-apply. Accept is the only pack/remat gate.
Remat fail ≠ accepted (pack rolled back). No public UI.

Queue files: data/ops/nfl-daily-intel/queue/runtime/ (gitignored).

Usage:
  # Desk OS item B — morning loop (one command)
  python scripts/nfl/queue_camp_sot_flags.py --morning

  python scripts/nfl/queue_camp_sot_flags.py --scan
  python scripts/nfl/queue_camp_sot_flags.py --queue
  python scripts/nfl/queue_camp_sot_flags.py --scan-txns
  # Desk OS item C: --scan-txns also prints Sleeper unmatched ID miss list (no roster rewrite)
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
from typing import Any, List, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
MS = REPO / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_camp_sot_queue import (  # noqa: E402
    DEFAULT_OVERDUE_HOURS,
    NOTES_MAY_TOUCH_MEANS,
    PROPOSALS_MAY_AUTO_APPLY,
    DepthSotWorkItem,
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
from src.services.nfl_txn_sot_scan import (  # noqa: E402
    collect_sleeper_id_misses,
    format_scan_table,
    format_sleeper_miss_table,
    ingest_txn_events,
    queue_txn_flags,
    scan_txn_flags,
    write_sleeper_miss_log,
)

# Pack already carries these SoT accepts — txn scan must not open new T1s for them.
ALREADY_IN_SOT = (
    "HOU Jayden Higgins",
    "BAL Danny Pinter",
    "LAC Tyler Biadasz",
    "NYG Calvin Austin III",
    "CLE Deshaun Watson",
    "WAS Laremy Tunsil",
    "WAS Brandon Coleman",
)


def _source_label(flag: DepthSotWorkItem) -> str:
    wid = flag.work_item_id or ""
    if "injury-report" in wid or "report" in wid:
        return "sleeper-report"
    if "txn" in wid or any(
        isinstance(s, dict) and str(s.get("source") or "") in {"sleeper", "pfr"}
        for s in (flag.sources or [])
    ):
        src = next(
            (
                str(s.get("source"))
                for s in (flag.sources or [])
                if isinstance(s, dict) and s.get("source")
            ),
            "txn",
        )
        return src
    return "camp_desk"


def _collect_alert_flags(
    *,
    overdue_hours: int | None,
    latest_desk_only: bool,
    as_of: str | None,
    with_pfr: bool,
    force_refresh: bool,
) -> Tuple[List[DepthSotWorkItem], dict[str, Any]]:
    """Camp + injury-report + txn open work items for --alert-t1 / --morning."""
    camp = scan_camp_sot_flags(
        overdue_hours=overdue_hours,
        latest_desk_only=latest_desk_only,
    )
    report_items, _, report_meta = scan_injury_report()
    txn_events = ingest_txn_events(
        as_of_date=as_of,
        with_pfr=with_pfr,
        force_refresh=force_refresh,
    )
    txn_flags = scan_txn_flags(
        events=txn_events,
        overdue_hours=overdue_hours,
    )
    meta = {
        "camp": len(camp),
        "injury_report": len(report_items),
        "txn": len(txn_flags),
        "report_as_of": (report_meta or {}).get("as_of"),
    }
    return list(camp) + list(report_items) + list(txn_flags), meta


def _print_alert(alerts: Sequence[DepthSotWorkItem], *, as_json: bool) -> int:
    payload = {
        "alert": "t1_past_kei_publish",
        "count": len(alerts),
        "work_item_ids": [f.work_item_id for f in alerts],
        "teams": [f.team for f in alerts],
        "sources": sorted({_source_label(f) for f in alerts}),
        "rows": [
            {
                "work_item_id": f.work_item_id,
                "team": f.team,
                "source": _source_label(f),
                "status": f.status,
                "overdue": f.overdue,
                "overdue_reason": f.overdue_reason,
            }
            for f in alerts
        ],
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        src = ",".join(payload["sources"]) or "none"
        print(
            f"T1 past KEI publish: {len(alerts)} "
            f"teams={','.join(f.team for f in alerts) or 'none'} "
            f"sources={src}"
        )
        for row in payload["rows"]:
            print(
                f"  source={row['source']} {row['team']} {row['work_item_id']} "
                f"status={row['status']}"
            )
    return 1 if alerts else 0


def _run_scan_txns(args: argparse.Namespace) -> Tuple[List[DepthSotWorkItem], int]:
    events = ingest_txn_events(
        as_of_date=args.as_of,
        with_pfr=args.with_pfr,
        force_refresh=args.force_refresh,
    )
    flags = scan_txn_flags(
        events=events,
        overdue_hours=args.overdue_hours,
    )
    summary = overdue_summary(flags)
    t1s = [f for f in flags if f.tier == "T1"]
    # Desk OS item C — print-only unmatched Sleeper IDs (no roster rewrite).
    misses = collect_sleeper_id_misses(events)
    miss_path = write_sleeper_miss_log(
        misses,
        as_of_date=str(args.as_of or (misses[0].as_of_date if misses else "")),
    )

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summary,
                    "already_in_sot_skip": list(ALREADY_IN_SOT),
                    "t1": [f.as_dict() for f in t1s],
                    "work_items": [f.as_dict() for f in flags],
                    "sleeper_unmatched": [m.as_dict() for m in misses],
                    "sleeper_unmatched_count": len(misses),
                    "accepts_performed": 0,
                },
                indent=2,
            )
        )
    else:
        tiers = summary["by_tier"]
        print(
            f"txn-scan material={summary['total_material']} "
            f"T1={tiers['T1']} T2={tiers['T2']} T3={tiers['T3']} "
            f"open={summary['open']} queued={summary['queued']} "
            f"overdue={summary['overdue']}"
        )
        print(
            "contract: feed≠means; patch≠auto; no depth invent; "
            "no ATL race close; no auto-accept; already-in-SoT skipped"
        )
        print("already-in-SoT (expect no new T1): " + "; ".join(ALREADY_IN_SOT))
        print()
        print("T1 candidates (no accepts unless desk marks):")
        print(format_scan_table(t1s))
        print()
        print("All txn flags:")
        print(format_scan_table(flags))
        print()
        print(
            f"=== Desk OS item C: Sleeper unmatched ID miss list "
            f"(n={len(misses)}; print only — no roster rewrite) ==="
        )
        print(format_sleeper_miss_table(misses))
        if miss_path:
            print(f"miss log (gitignored): {miss_path}")

    if args.queue:
        result = queue_txn_flags(
            flags,
            only_overdue=args.only_overdue,
            only_with_drafts=args.only_with_drafts,
            tiers=args.tier,
        )
        if args.json:
            print(json.dumps({"queue": result.as_dict()}, indent=2))
        else:
            print(
                f"txn queue idempotent: created={len(result.created)} "
                f"updated={len(result.updated)} unchanged={len(result.unchanged)} "
                f"skipped={len(result.skipped)}"
            )
            for path in result.written:
                print(f"  {path}")
    return flags, 0


def _run_scan_report(args: argparse.Namespace) -> Tuple[List[DepthSotWorkItem], int]:
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
    return list(items), 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Print open/overdue DepthSotWorkItems")
    ap.add_argument("--queue", action="store_true", help="Upsert work items into queue/runtime/")
    ap.add_argument(
        "--morning",
        action="store_true",
        help="Desk OS item B morning loop: --scan-txns + --scan-report + --alert-t1",
    )
    ap.add_argument(
        "--scan-txns",
        action="store_true",
        help="Scan Sleeper (+ optional PFR) vs live pack → T1/T2 txn work items (no accept)",
    )
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
        help="Exit 1 if any T1 is still open past next KEI publish (camp + report + txn)",
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
    ap.add_argument(
        "--with-pfr",
        action="store_true",
        help="With --scan-txns / --morning: also soft-fetch PFR month transactions",
    )
    ap.add_argument(
        "--as-of",
        default=None,
        help="With --scan-txns / --morning: as_of_date YYYY-MM-DD (default ET today)",
    )
    ap.add_argument(
        "--force-refresh",
        action="store_true",
        help="With --scan-txns / --morning: bypass Sleeper/PFR cache TTL",
    )
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    args = ap.parse_args()

    # --morning expands to the three morning-loop legs.
    if args.morning:
        args.scan_txns = True
        args.scan_report = True
        args.alert_t1 = True

    actions = [
        args.scan,
        args.queue,
        args.morning,
        args.scan_txns,
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
            "pass --morning, --scan, --queue, --scan-txns, --scan-defense, --queue-defense, "
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

    # Morning loop / combined legs: txns → report → alert (alert last for exit code).
    morning_mode = bool(args.morning)
    ran_txn = False
    ran_report = False

    if args.scan_txns:
        if morning_mode:
            print("=== morning: --scan-txns ===")
        _run_scan_txns(args)
        ran_txn = True
        if not morning_mode and not args.alert_t1 and not args.scan_report:
            return 0

    if args.scan_report or args.queue_report:
        if morning_mode:
            print()
            print("=== morning: --scan-report ===")
        # queue_report alone without scan_report still works via this branch
        if not args.scan_report and args.queue_report:
            args.scan_report = True
        _run_scan_report(args)
        ran_report = True
        if not morning_mode and not args.alert_t1 and not args.scan_txns:
            return 0

    if args.alert_t1:
        if morning_mode:
            print()
            print("=== morning: --alert-t1 ===")
        all_flags, meta = _collect_alert_flags(
            overdue_hours=args.overdue_hours,
            latest_desk_only=not args.all_dates,
            as_of=args.as_of,
            with_pfr=args.with_pfr,
            force_refresh=args.force_refresh,
        )
        if args.json and morning_mode:
            print(json.dumps({"morning_meta": meta}, indent=2))
        elif morning_mode:
            print(
                f"morning sources: camp={meta['camp']} "
                f"report={meta['injury_report']} txn={meta['txn']}"
            )
        alerts = t1_past_kei_publish(all_flags)
        return _print_alert(alerts, as_json=args.json)

    if ran_txn or ran_report:
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
