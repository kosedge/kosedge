#!/usr/bin/env python3
"""Local sealed-tree contract check. Synthetic / sealed trees only.

Not a runner and not a gate. Does not live under scripts/nfl/imv/.
Does not open a database or fetch odds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))

from src.services.nfl_eval_prep.local_tree_check import (  # noqa: E402
    LocalTreeCheckError,
    check_local_tree,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NFL eval-prep local tree check (not a gate, no eval)"
    )
    parser.add_argument("root", help="Local sealed input directory")
    args = parser.parse_args()
    try:
        result = check_local_tree(args.root)
    except LocalTreeCheckError as exc:
        print(json.dumps({"status": "REFUSED", "gate": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
