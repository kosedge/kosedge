#!/usr/bin/env python3
"""Research-only 2026 W−1 raw unadjusted team-game metrics.

Usage:
  python scripts/cfb/run_2026_w1_team_game_metrics.py
  python scripts/cfb/run_2026_w1_team_game_metrics.py --as-of 20260915 --as-of-week 3
  python scripts/cfb/run_2026_w1_team_game_metrics.py --commit-ops

Does not write the 2014–2025 historical lake. Does not call CFBD.
Does not change SP+ compose / KEI / Edge Board. Not KE Ratings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.team_game_w1_2026 import (  # noqa: E402
    run_research_pipeline,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default=None, help="YYYYMMDD stamp (default: today UTC)")
    parser.add_argument(
        "--as-of-week",
        type=int,
        default=None,
        help="Predictive week W (eligibility is week < W). Default: max completed week + 1",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help="Override research dest dir (must not be historical lake)",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not download; require existing parquet in dest",
    )
    parser.add_argument(
        "--commit-ops",
        action="store_true",
        help="Write slim evidence under data/ops/cfb-2026-w1-raw-team-game-20260915/",
    )
    args = parser.parse_args(argv)
    dest = Path(args.dest) if args.dest else None
    result = run_research_pipeline(
        as_of=args.as_of,
        as_of_week=args.as_of_week,
        dest_dir=dest,
        allow_fetch=not args.no_fetch,
        write_artifacts=True,
        commit_ops=args.commit_ops,
    )
    summary = result["summary"]
    validation = result["validation"]
    print(json.dumps(
        {
            "passed": validation.get("passed"),
            "as_of": summary.get("as_of"),
            "as_of_week": summary.get("as_of_week"),
            "eligible_count": summary.get("eligible_count"),
            "table_rows": summary.get("table_rows"),
            "table_games": summary.get("table_games"),
            "reason_counts": summary.get("reason_counts"),
            "checks": validation.get("checks"),
            "pbp_sha256": validation.get("pbp_sha256"),
            "schedule_sha256": validation.get("schedule_sha256"),
            "dest": result.get("dest"),
            "product_label": summary.get("product_label"),
            "opponent_adjusted": False,
            "not_ke_ratings": True,
        },
        indent=2,
    ))
    return 0 if validation.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
