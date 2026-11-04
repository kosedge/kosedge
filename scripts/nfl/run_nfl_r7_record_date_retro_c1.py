#!/usr/bin/env python3
"""R7_RECORD_DATE_RETRO_C1 guarded synthetic executor. CERT=0. No real EXEC."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_r7_record_date_retro_c1.produce import main


if __name__ == "__main__":
    raise SystemExit(main())
