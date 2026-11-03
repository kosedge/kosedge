#!/usr/bin/env python3
"""ONE NFL_JOINT_CONTRACT_V1 literal-law command.

Synthetic oracle → adapter → consume → handoff. CERT=0.
Not the Primary A evidence-manifest gate. Not a fitted joint-family.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_joint_contract_v1_literal_law.py
  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_joint_contract_v1_literal_law.py /tmp/nfl-joint-contract-v1
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_joint_contract_v1.run import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
