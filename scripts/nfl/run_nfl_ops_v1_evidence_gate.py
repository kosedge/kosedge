#!/usr/bin/env python3
"""ONE NFL_OPS_V1 evidence-manifest command (Primary A).

Accepted synthetic W-FIX producer → actual consumer → evidence gate.
CERT=0. Does not run inherited #700/#701 real-outcome tests.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_ops_v1_evidence_gate.py
  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_ops_v1_evidence_gate.py /tmp/nfl-ops-v1-evidence
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_ops_v1_evidence.run import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
