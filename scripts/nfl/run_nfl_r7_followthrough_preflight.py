#!/usr/bin/env python3
"""t5335u R7 followthrough metadata preflight. CERT=0. No NTBB-K kernel."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_r7_correctness_v1.followthrough_preflight import main


if __name__ == "__main__":
    raise SystemExit(main())
