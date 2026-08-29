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

from src.services.nfl_txn_depth_sot import (  # noqa: E402
    CACHE_DIR_DEFAULT,
    FEED_MAY_WRITE_MEANS,
    FEED_MAY_WRITE_PACK,
    LIVE_PROVE_WATCH,
    assert_feed_cannot_mutate_pack_or_means,
    collect_events,
    fetch_sleeper_players,
    format_scan_table,
    queue_txn_flags,
    scan_txn_depth_flags,
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
    ap.add_argument("--as-of", default="", help="as_of_date YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--cache-dir", type=Path, default=CACHE_DIR_DEFAULT)
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

    if FEED_MAY_WRITE_PACK or FEED_MAY_WRITE_MEANS:
        print("FATAL: txn feed must not write pack/means", file=sys.stderr)
        return 2
    assert_feed_cannot_mutate_pack_or_means()

    if args.refresh_cache and not (args.scan or args.queue):
        path = fetch_sleeper_players(cache_dir=args.cache_dir, force=True)
        # fetch returns dict; cache path printed via save
        print(f"sleeper cache refreshed under {args.cache_dir} players={len(path)}")
        return 0

    as_of = args.as_of.strip() or None
    events = collect_events(
        include_pfr=args.include_pfr,
        as_of_date=as_of,
        cache_dir=args.cache_dir,
        force_refresh=args.refresh_cache,
    )
    result = scan_txn_depth_flags(events=events, watch_names=LIVE_PROVE_WATCH)

    if args.scan:
        if args.json:
            print(json.dumps(result.as_dict(), indent=2))
        else:
            print(format_scan_table(result))
            # Explicit live-prove lines for desk-accepted names
            print("\nLIVE PROVE (no accepts):")
            for name in ("Jayden Higgins", "Danny Pinter", "Tyler Biadasz", "Calvin Austin"):
                rows = [
                    r
                    for r in result.table
                    if name.lower() in r.player_name.lower()
                    or r.player_name.lower() in name.lower()
                ]
                if not rows:
                    print(f"  {name}: no feed hit / no new T1")
                else:
                    for r in rows:
                        print(
                            f"  {r.player_name} ({r.team}): {r.disposition} "
                            f"event={r.event} pack={r.pack_injury or '—'} "
                            f"(tier={r.tier or '—'})"
                        )

    if args.queue:
        q = queue_txn_flags(result.items, tiers=args.tier)
        if args.json:
            print(json.dumps(q.as_dict(), indent=2))
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
