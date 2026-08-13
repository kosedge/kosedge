#!/usr/bin/env python3
"""Apply approved daily-intel overrides to the one NFL depth SoT pack.

Does not invent a second depth map. Does not auto-run 100k.

Usage:
  python scripts/nfl/apply_daily_intel_overrides.py \\
      --overrides data/ops/nfl-daily-intel/sample-override.example.json --dry-run

  python scripts/nfl/apply_daily_intel_overrides.py \\
      --overrides path.json --write
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

from src.services.nfl_daily_intel import (  # noqa: E402
    PACK_DEFAULT,
    apply_intel_overrides,
    format_smoke_diff,
    kei_smoke_for_teams,
    load_override_file,
)

DEFAULT_EXAMPLE = REPO / "data" / "ops" / "nfl-daily-intel" / "sample-override.example.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--overrides", type=Path, required=True, help="Approved override JSON")
    ap.add_argument("--pack", type=Path, default=PACK_DEFAULT, help="Depth SoT pack path")
    ap.add_argument("--dry-run", action="store_true", help="Print diff; do not write (default)")
    ap.add_argument("--write", action="store_true", help="Write pack in place")
    ap.add_argument(
        "--allow-fixture",
        action="store_true",
        help="Allow --write when the override file is marked fixture:true",
    )
    args = ap.parse_args()
    dry = not args.write

    ov_doc = load_override_file(args.overrides)
    if ov_doc.get("fixture") and args.write and not args.allow_fixture:
        print("refusing --write on fixture override file (pass --allow-fixture to override)", file=sys.stderr)
        return 2

    pack = json.loads(args.pack.read_text(encoding="utf-8"))
    overrides = ov_doc.get("overrides") or []
    as_of = str(ov_doc.get("as_of") or "")
    before_teams = sorted(
        {
            str(o.get("team") or "")
            for o in overrides
            if o.get("team")
        }
    )
    before_smoke = kei_smoke_for_teams(pack, before_teams) if before_teams else []
    result = apply_intel_overrides(pack, overrides, as_of=as_of or None)
    after_smoke = (
        kei_smoke_for_teams(result.payload, result.touched_teams)
        if result.touched_teams
        else []
    )

    print(json.dumps(result.as_dict(), indent=2))
    print("--- KEI Week 1 smoke (touched teams) ---")
    for line in format_smoke_diff(before_smoke, after_smoke):
        print(line)
    if result.republish_recommended:
        print("RESEARCH REPUBLISH RECOMMENDED (do not auto-100k):")
        for reason in result.republish_reasons:
            print(f"  - {reason}")

    if dry:
        print("dry-run: pack not written")
        return 0

    args.pack.write_text(json.dumps(result.payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
