#!/usr/bin/env python3
"""Close + grade The Book CFB slate (official final only).

No lookahead. Skips in-progress. late_post CLV tagged after_open.
Does not invent grades.

Usage:
  BOOK_LEDGER_DIR=data/ops/book PYTHONPATH=services/model-service:. \\
    python scripts/cfb/book_close_grade.py --date 2026-08-29 --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.book_ledger.grade import close_and_grade_slate  # noqa: E402
from src.services.book_ledger.store import BookStore  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="The Book — CFB close+grade")
    ap.add_argument("--date", required=True, help="Slate date YYYY-MM-DD")
    ap.add_argument("--include-aug30-late", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Print actions; do not settle")
    ap.add_argument(
        "--ledger-dir",
        default=None,
        help="Override BOOK_LEDGER_DIR (default env or data/ops/book)",
    )
    args = ap.parse_args()

    store = BookStore(root=Path(args.ledger_dir)) if args.ledger_dir else None
    extra = ["2026-08-30"] if args.include_aug30_late else None
    summary = close_and_grade_slate(
        week_or_slate=args.date,
        extra_dates=extra,
        store=store,
        dry_run=args.dry_run,
    )
    print("=== The Book — CFB close+grade ===")
    print(f"slate:    {summary['week_or_slate']}")
    print(f"dry_run:  {summary['dry_run']}")
    print(f"pending:  {summary['n_pending_in']}")
    print(f"settled:  {summary['n_settled']}")
    print(f"void:     {summary['n_void']}")
    print(f"skipped:  {summary['n_skipped']}")
    for a in summary.get("actions") or []:
        late = " LATE" if a.get("late_post") else ""
        print(
            f"  {a.get('away')}@{a.get('home')}  {a.get('action')}  "
            f"reason={a.get('reason')}  result={a.get('result')}  "
            f"clv_note={a.get('clv_note')}{late}"
        )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
