#!/usr/bin/env python3
"""ONE NFL_JOINT_CONTRACT_V1 integrated command.

adapter → consume_literal_law → primary evidence/ownership DIRECT gates.
CERT=0. SYNTHETIC_JOINT_LITERAL_LAW. Not the W-FIX point-margin profile.

From repo root:
  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_joint_contract_v1_integrated.py
  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_joint_contract_v1_integrated.py /tmp/nfl-joint-contract-v1-integrated
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.services.nfl_joint_contract_v1.integrate import run_joint_integrated_command  # noqa: E402
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse  # noqa: E402


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dest = Path(args[0]) if args else Path("/tmp/nfl-joint-contract-v1-integrated")
    try:
        result = run_joint_integrated_command(dest_dir=dest)
    except JointContractRefuse as exc:
        print(f"REFUSE [{exc.refuse_class}] {exc.reason}", file=sys.stderr)
        return 2
    print(f"status {result.get('status')}")
    print(f"profile {result.get('profile')}")
    print(f"digest {result.get('common_digest')}")
    print(f"ready_for_review {str(result.get('ready_for_review')).lower()}")
    print("cert 0")
    print(f"not_integrated_through_evidence_gate {str(result.get('not_integrated_through_evidence_gate')).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
