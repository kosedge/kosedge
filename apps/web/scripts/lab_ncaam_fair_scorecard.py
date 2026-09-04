#!/usr/bin/env python3
"""CLI: first frozen NCAAM Fair Lab scorecard (Contract v1 / Phase E).

Research only — scores Train-A + Test-A fair parquet vs B1/B2.
Does not write Edge Board / kei_lines / PLAY tags. No peek-tune.

Usage (from repo root):
  python3 apps/web/scripts/lab_ncaam_fair_scorecard.py
  python3 scripts/lab/ncaam_fair_scorecard.py   # thin wrapper
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
SRC = WEB / "src"

for p in (str(WEB), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    parser = argparse.ArgumentParser(description="NCAAM Fair Lab scorecard (research only)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Lab artifact dir (default: data/ops/lab/ncaam)",
    )
    parser.add_argument(
        "--actuals",
        type=Path,
        default=None,
        help="Optional actual_margins.parquet override",
    )
    parser.add_argument(
        "--no-densify",
        action="store_true",
        help="Use thin event_id→actual_margins only (frozen v1 baseline path)",
    )
    parser.add_argument(
        "--overwrite-frozen-v1",
        action="store_true",
        help="Allow overwriting frozen v1 scorecard artifacts (default: refuse when densified)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute scorecard JSON only; no artifact writes",
    )
    args = parser.parse_args()

    from ncaam_lab.scorecard import build_scorecard, write_scorecard_artifacts

    densify = not args.no_densify
    card = build_scorecard(
        out_dir=args.out_dir,
        actuals_path=args.actuals,
        densify_results=densify,
    )
    if args.dry_run:
        print(json.dumps({
            "grades": card["grades"],
            "subscriber_influence": card["subscriber_influence"],
            "leakage_receipt": card["leakage_receipt"],
            "results_densify": densify,
            "test_a_predictive": (card.get("cuts") or {}).get("test_a", {}).get("predictive"),
            "test_a_market_edge": (card.get("cuts") or {}).get("test_a", {}).get("market_edge"),
        }, indent=2))
        return 0

    paths = write_scorecard_artifacts(
        card,
        out_dir=args.out_dir,
        overwrite_frozen_v1=args.overwrite_frozen_v1 or (not densify),
    )
    summary = {
        "grades": card["grades"],
        "subscriber_influence": card["subscriber_influence"],
        "leakage_receipt": card["leakage_receipt"],
        "results_densify": densify,
        "outputs": paths,
        "product_side_effects": "none",
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
