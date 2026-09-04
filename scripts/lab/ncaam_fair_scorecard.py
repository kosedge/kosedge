#!/usr/bin/env python3
"""Thin repo-root wrapper → apps/web Lab fair scorecard CLI."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "web"
    / "scripts"
    / "lab_ncaam_fair_scorecard.py"
)


def main() -> int:
    if not TARGET.is_file():
        print(f"Missing canonical CLI: {TARGET}", file=sys.stderr)
        return 1
    sys.argv[0] = str(TARGET)
    runpy.run_path(str(TARGET), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
