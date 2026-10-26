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
    spec_sha256,
    weekly_pipeline_schedule_enabled,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="t4359u local NFL fair-line path")
    parser.add_argument("--fixture", choices=("demo",), help="Built-in HOME demo card")
    parser.add_argument("--card", type=Path, help="JSON game card or {cards:[...]}")
    parser.add_argument("--out", type=Path, help="Write JSON receipt")
    args = parser.parse_args()

    if weekly_pipeline_schedule_enabled():
        print(
            "BLOCKED: NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED is on. "
            "t4359u local path refuses Beat/cron.",
            file=sys.stderr,
        )
        return 2

    cards = []
    if args.fixture == "demo":
        cards.append(demo_home_card())
    if args.card:
        cards.extend(load_cards(args.card))
    if not cards:
        parser.error("pass --fixture demo and/or --card PATH")

    if len(cards) == 1:
        payload = run_local_fair_line(cards[0])
    else:
        payload = run_local_slate(cards)
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
    return 0 if payload.get("status") in {"READY", None} and payload.get("n_blocked", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
