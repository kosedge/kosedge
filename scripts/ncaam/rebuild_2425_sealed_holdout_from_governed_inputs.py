#!/usr/bin/env python3
"""DEPRECATED entrypoint — Path B recovery is now R2 hydrate (Phase 2.6F CR4).

Authoritative disaster recovery:
  python scripts/ncaam/recover_2425_sealed_holdout_from_r2.py \\
      --governed-evaluator --authorize-unseal

Forensic raw+KenPom+odds reconstruction (cannot promote frozen holdout):
  python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py

This script refuses to rebuild/promote the frozen holdout from governed inputs.
Raw+KenPom+odds must NOT redefine the frozen v1.1 package.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--forensic",
        action="store_true",
        help="Delegate to forensic_rebuild_2425_from_raw_kenpom_odds.py (no live promote).",
    )
    args = parser.parse_args(argv)
    if args.forensic:
        from pathlib import Path
        import runpy

        script = (
            Path(__file__).resolve().parent
            / "forensic_rebuild_2425_from_raw_kenpom_odds.py"
        )
        sys.argv = [str(script)] + (["--dry-run"] if args.dry_run else [])
        runpy.run_path(str(script), run_name="__main__")
        return 0
    receipt = {
        "status": "REFUSED_SUPERSEDED_BY_CR4_R2_RECOVERY",
        "phase": "2.6F-CR4",
        "message": (
            "Path B rebuild-from-governed-inputs no longer defines the frozen "
            "holdout. Use recover_2425_sealed_holdout_from_r2.py for authoritative "
            "disaster recovery (exact R2 bytes). Use "
            "forensic_rebuild_2425_from_raw_kenpom_odds.py for investigation only."
        ),
        "authoritative_recovery": "scripts/ncaam/recover_2425_sealed_holdout_from_r2.py",
        "forensic_path": "scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py",
        "may_promote_frozen_holdout": False,
        "odds_api_calls_made": False,
        "dry_run": args.dry_run,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
