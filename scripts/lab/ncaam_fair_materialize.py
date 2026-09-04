#!/usr/bin/env python3
"""Thin repo-root wrapper → apps/web Lab fair materialize CLI.

Canonical entrypoint (allowlisted web Python):
  apps/web/scripts/lab_ncaam_fair_materialize.py

This wrapper exists for ergonomic `scripts/lab/` parity with NFL Lab runners.
It is outside apps/web and is not part of the web Python allowlist.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "web"
    / "scripts"
    / "lab_ncaam_fair_materialize.py"
)


def main() -> int:
    if not TARGET.is_file():
        print(f"Missing canonical CLI: {TARGET}", file=sys.stderr)
        return 1
    # Preserve argv for argparse inside the target.
    sys.argv[0] = str(TARGET)
    runpy.run_path(str(TARGET), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
