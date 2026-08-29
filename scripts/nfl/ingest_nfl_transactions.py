#!/usr/bin/env python3
"""Free NFL transaction ingest → DepthSot T1/T2 scanner (no auto-accept).

Sources:
  - Sleeper GET https://api.sleeper.app/v1/players/nfl (gitignored cache, TTL 1–2h)
  - Optional PFR current-month placed-on-IR / activated / waived-injured

Diff vs live pack injury_status + depth_order. Opens proposed_patch queue items only.
Never writes pack / means / fantasy / props. Never crowns WR1/QB1 from Sleeper depth.

Usage:
  python scripts/nfl/ingest_nfl_transactions.py --scan
  python scripts/nfl/ingest_nfl_transactions.py --scan --json
  python scripts/nfl/ingest_nfl_transactions.py --queue   # upsert proposed_patch only
  python scripts/nfl/ingest_nfl_transactions.py --refresh-cache
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
    NOTES_MAY_TOUCH_MEANS,
    PROPOSALS_MAY_AUTO_APPLY,
    overdue_summary,
)
from src.services.nfl_txn_sot_scan import (  # noqa: E402
    CACHE_DIR_DEFAULT,
    format_scan_table,
    ingest_txn_events,
    load_sleeper_players,
    queue_txn_flags,
    scan_txn_flags,
)

# Desk-accepted / already in live pack — expect no new T1 from this feed.
ALREADY_IN_SOT = (
    "HOU Jayden Higgins",
    "BAL Danny Pinter",
    "LAC Tyler Biadasz",
    "NYG Calvin Austin III",
    "CLE Deshaun Watson",
    "WAS Laremy Tunsil",
    "WAS Brandon Coleman",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true", help="Diff feed vs pack; print table (no accept)")
    ap.add_argument(
        "--queue",
        action="store_true",
        help="Upsert proposed_patch work items into queue/runtime/ (idempotent)",
    )
    ap.add_argument("--refresh-cache", action="store_true", help="Force Sleeper cache refresh")
    ap.add_argument("--include-pfr", action="store_true", help="Best-effort PFR month scrape")
    ap.add_argument("--with-pfr", action="store_true", help="Alias for --include-pfr")
    ap.add_argument("--as-of", default=None, help="as_of_date YYYY-MM-DD (default: today ET)")
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--force-refresh", action="store_true", help="Bypass Sleeper/PFR cache TTL")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    ap.add_argument(
        "--tier",
        action="append",
        choices=["T1", "T2"],
        help="With --queue: only these tiers",
    )
    args = ap.parse_args()

    if not any([args.scan, args.queue, args.refresh_cache]):
        ap.error("pass --scan, --queue, and/or --refresh-cache")

    if NOTES_MAY_TOUCH_MEANS or PROPOSALS_MAY_AUTO_APPLY:
        print("FATAL: txn feed must not write pack/means", file=sys.stderr)
        return 2

    cache_dir = args.cache_dir or CACHE_DIR_DEFAULT
    if args.refresh_cache and not (args.scan or args.queue):
        payload = load_sleeper_players(cache_dir=cache_dir, force_refresh=True)
        print(f"sleeper cache refreshed under {cache_dir} players={len(payload)}")
        return 0

    events = ingest_txn_events(
        as_of_date=args.as_of,
        with_pfr=bool(args.include_pfr or args.with_pfr),
        force_refresh=bool(args.force_refresh or args.refresh_cache),
        cache_dir=cache_dir,
    )
    flags = scan_txn_flags(events=events)
    summary = overdue_summary(flags)
    t1s = [f for f in flags if f.tier == "T1"]

    if args.scan:
        if args.json:
            print(
                json.dumps(
                    {
                        "summary": summary,
                        "already_in_sot_skip": list(ALREADY_IN_SOT),
                        "t1": [f.as_dict() for f in t1s],
                        "work_items": [f.as_dict() for f in flags],
                        "contract": {
                            "feed_may_write_pack": False,
                            "feed_may_write_means": False,
                            "proposals_may_auto_apply": False,
                            "accepts_in_this_pr": False,
                        },
                    },
                    indent=2,
                )
            )
        else:
            print(
                f"txn-scan material={summary['total_material']} "
                f"T1={summary['by_tier']['T1']} T2={summary['by_tier']['T2']}"
            )
            print("already-in-SoT (expect no new T1): " + "; ".join(ALREADY_IN_SOT))
            print("\nT1 candidates (DO NOT ACCEPT in this PR):")
            print(format_scan_table(t1s))
            print("\nAll txn flags:")
            print(format_scan_table(flags))
            # Explicit prove lines for Higgins / Pinter / Biadasz / Austin
            print("\nLIVE PROVE (print only — no accepts):")
            for label in (
                "Jayden Higgins",
                "Danny Pinter",
                "Tyler Biadasz",
                "Calvin Austin",
            ):
                hits = [f for f in t1s if label.lower() in (f.title or "").lower()]
                if hits:
                    print(f"  FAIL {label}: would open T1 (unexpected)")
                else:
                    print(f"  OK   {label}: no new T1")

    if args.queue:
        q = queue_txn_flags(flags, tiers=args.tier)
        if args.json:
            print(json.dumps({"queue": q.as_dict()}, indent=2))
        else:
            print(
                f"txn queue idempotent: created={len(q.created)} "
                f"updated={len(q.updated)} unchanged={len(q.unchanged)} "
                f"skipped={len(q.skipped)}"
            )
            for path in q.written:
                print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
