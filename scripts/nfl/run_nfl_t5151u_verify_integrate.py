#!/usr/bin/env python3
"""t5153u ONE offline verification/integration command.

Loads/hashes/verifies the immutable published DEV437 result (66c3bde1)
and matched72 result (#693 tip 316345fa), plus accepted REG496 / 502 /
Package A pins. A cohort gates then B numerical checks. Writes one
machine-readable receipt. Fixtures stay in test helpers only.
Nonzero failure prevents VERIFIED/final output. No real EVAL.
CERT=0. DRAFT≠merge.

Exact command:
  python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.verify_integrate import (  # noqa: E402
    VerifyIntegrateRefuse,
    run_one_command,
)


def main() -> int:
    try:
        receipt = run_one_command(root=ROOT)
    except VerifyIntegrateRefuse as exc:
        print(json.dumps({"ok": False, "error": str(exc), "verified": False}, indent=2))
        dest = ROOT / "data/ops/nfl-t5151u-verify-integrate/RECEIPT.json"
        if dest.is_file():
            print(f"receipt={dest}", file=sys.stderr)
        return 1
    print(json.dumps(
        {
            "ok": True,
            "verified": False,
            "status": receipt["status"],
            "stop": receipt["stop"],
            "receipt": receipt["receipt_path"],
            "tip_sha": receipt["tip_sha"],
            "cert_candidate": receipt["cert_candidate"],
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
