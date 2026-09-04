#!/usr/bin/env python3
"""Thin wrapper → apps/web/scripts/lab_ncaam_results_coverage_receipt.py"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "apps" / "web" / "scripts" / "lab_ncaam_results_coverage_receipt.py"


def main() -> int:
    sys.argv[0] = str(SCRIPT)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
