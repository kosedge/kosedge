#!/usr/bin/env python3
"""t4359u local fair-line runner. Scheduling off. No deploy. No publication.

Examples:
  python3 scripts/nfl/run_nfl_enterprise_green_local.py --fixture demo
  python3 scripts/nfl/run_nfl_enterprise_green_local.py --card /tmp/card.json
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

from src.services.nfl_enterprise_green_path import (  # noqa: E402
    SPEC_ID,
    SPEC_VERSION,
    demo_home_card,
    load_cards,
    packaged_epa_sha256,
    run_local_fair_line,
    run_local_slate,
    run_local_week,
    spec_sha256,
    week6_boundary_slate,
    weekly_pipeline_schedule_enabled,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="t4359u/t4366u local NFL fair-line path")
    parser.add_argument(
        "--fixture",
        choices=("demo", "week6"),
        help="demo = one HOME card; week6 = local weekly slate (T7 neutrals stay blocked)",
    )
    parser.add_argument("--card", type=Path, help="JSON game card, slate, or {cards:[...]}")
    parser.add_argument("--out", type=Path, help="Write JSON receipt")
    args = parser.parse_args()

    if weekly_pipeline_schedule_enabled():
        print(
            "BLOCKED: NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED is on. "
            "t4359u local path refuses Beat/cron.",
            file=sys.stderr,
        )
        return 2

    payload: dict
    if args.fixture == "week6":
        payload = run_local_week(week6_boundary_slate())
    elif args.card and args.card.is_file():
        raw = json.loads(args.card.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("cards"), list) and (
            "week" in raw or "season" in raw
        ):
            payload = run_local_week(raw)
        else:
            cards = load_cards(args.card)
            if args.fixture == "demo":
                cards = [demo_home_card(), *cards]
            payload = run_local_fair_line(cards[0]) if len(cards) == 1 else run_local_slate(cards)
    elif args.fixture == "demo":
        payload = run_local_fair_line(demo_home_card())
    else:
        parser.error("pass --fixture demo|week6 and/or --card PATH")

    payload = dict(payload)
    payload["packaged_epa_sha256"] = packaged_epa_sha256()
    payload.setdefault("spec_id", SPEC_ID)
    payload.setdefault("spec_version", SPEC_VERSION)
    payload.setdefault("spec_sha256", spec_sha256())

    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    if payload.get("status") == "BLOCKED":
        return 1
    # Weekly slate: blocked T7 / missing-input rows are expected fail-closed.
    if payload.get("pipeline") == "local_weekly_manual":
        return 0 if int(payload.get("n_ready") or 0) >= 1 else 1
    return 0 if payload.get("status") == "READY" or int(payload.get("n_blocked") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
