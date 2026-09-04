#!/usr/bin/env python3
"""CLI: materialize NCAAM Lab fair research set (Contract v1 / Phase E).

Colocated with web Lab/pipeline Python (same house as ncaam_identity + CBB scripts).
Research only — does not write Edge Board / kei_lines product JSON.

Usage (from repo root):
  python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a
  python3 scripts/lab/ncaam_fair_materialize.py --cut train_a   # thin wrapper

Cut windows (LOCKED tip dates):
  train_a          2022-11-07 → 2023-03-12  (Valid-A folded in)
  test_a           2023-11-06 → 2024-01-28  (OOS)
  universe_path_a  2022-11-01 → 2024-01-28  (2025 pocket OUT)
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
    parser = argparse.ArgumentParser(description="NCAAM Lab fair materialize (research only)")
    parser.add_argument(
        "--cut",
        default="train_a",
        choices=["train_a", "test_a", "universe_path_a"],
        help="Locked cut window (default: train_a)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Artifact dir (default: data/ops/lab/ncaam)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute summary only; no writes")
    args = parser.parse_args()

    from ncaam_lab.materialize import materialize_lab_fair

    summary = materialize_lab_fair(
        cut=args.cut,
        out_dir=args.out_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
