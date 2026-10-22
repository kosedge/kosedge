#!/usr/bin/env python3
"""Local-path runner v2. Synthetic / sealed trees only. No eval seasons.

Does not live under scripts/nfl/imv/. Does not open a database or fetch odds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))

from src.services.nfl_eval_prep.runner_v2 import RunnerV2Error, run_local_rebuild  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="NFL eval-prep runner v2 (local path, no eval)")
    parser.add_argument("root", help="Local sealed input directory")
    args = parser.parse_args()
    try:
        result = run_local_rebuild(args.root)
    except RunnerV2Error as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
