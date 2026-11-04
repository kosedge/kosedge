#!/usr/bin/env python3
"""Observed-exit produce child for t5289u R7. CERT=0. SYNTHETIC only.

Parent binds this process's returncode. Do not treat as a receipt command.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_r7_correctness_v1.produce import produce_only_main


if __name__ == "__main__":
    raise SystemExit(produce_only_main())
