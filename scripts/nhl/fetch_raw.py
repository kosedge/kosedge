#!/usr/bin/env python3
"""Refresh NHL raw snapshots (official *.nhle.com only).

Usage:
  python3 scripts/nhl/fetch_raw.py
  python3 scripts/nhl/fetch_raw.py --status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nhl_data import (  # noqa: E402
    FETCHER_VERSION,
    documentation,
    load_goalie_box_pack,
    load_schedule_pack,
    load_skater_box_pack,
    load_team_box_pack,
    opening_night_has_fla_at_car,
    write_raw_snapshots,
)


def cmd_fetch() -> int:
    print(f"=== NHL raw fetch ({FETCHER_VERSION}) ===")
    summary = write_raw_snapshots()
    print(json.dumps(summary, indent=2))
    return 0


def cmd_status() -> int:
    sched = load_schedule_pack()
    teams = load_team_box_pack()
    skaters = load_skater_box_pack()
    goalies = load_goalie_box_pack()
    status = {
        "documentation": documentation(),
        "schedule_games": sched.get("n_games") or len(sched.get("games") or []),
        "team_rows": teams.get("n_teams") or len(teams.get("teams") or []),
        "skater_rows": skaters.get("n_rows"),
        "goalie_rows": goalies.get("n_rows"),
        "opening_fla_at_car": opening_night_has_fla_at_car(sched),
    }
    print(json.dumps(status, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NHL raw snapshot fetcher")
    ap.add_argument(
        "--status",
        action="store_true",
        help="Print snapshot status without refetching",
    )
    args = ap.parse_args()
    if args.status:
        return cmd_status()
    return cmd_fetch()


if __name__ == "__main__":
    raise SystemExit(main())
