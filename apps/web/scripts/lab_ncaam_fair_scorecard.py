#!/usr/bin/env python3
"""CLI: NCAAM Fair Lab scorecard (Contract v1 / Phase E).

Research only — scores Train-A + Test-A fair parquet vs B1/B2.
Does not write Edge Board / kei_lines / PLAY tags. No peek-tune.

Default (densify): freezes **v1.1** artifacts (distinct from frozen v1).
`--no-densify`: thin event_id path (v1 baseline; requires --overwrite-frozen-v1 to write).

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
        help="Allow overwriting frozen v1 scorecard artifacts (thin path only; densify never clobbers v1)",
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
            "scorecard_version": card.get("scorecard_version"),
            "grades": card["grades"],
            "subscriber_influence": card["subscriber_influence"],
            "leakage_receipt": card["leakage_receipt"],
            "results_densify": densify,
            "test_a_predictive": (card.get("cuts") or {}).get("test_a", {}).get("predictive"),
            "test_a_market_edge": (card.get("cuts") or {}).get("test_a", {}).get("market_edge"),
            "test_a_evidence": (card.get("cuts") or {}).get("test_a", {}).get("evidence"),
        }, indent=2))
        return 0

    # Densify → v1.1 paths. Thin → v1 only when overwrite flag set.
    overwrite_v1 = bool(args.overwrite_frozen_v1) and (not densify)
    paths = write_scorecard_artifacts(
        card,
        out_dir=args.out_dir,
        overwrite_frozen_v1=overwrite_v1,
    )
    summary = {
        "scorecard_version": card.get("scorecard_version"),
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
