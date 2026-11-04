#!/usr/bin/env python3
"""t5289u R7_CORRECTNESS_V1 integrated command. CERT=0. SYNTHETIC only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_r7_correctness_v1.run import main


if __name__ == "__main__":
    raise SystemExit(main())
