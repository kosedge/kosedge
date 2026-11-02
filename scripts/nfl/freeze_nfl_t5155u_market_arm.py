#!/usr/bin/env python3
"""t5155u market-arm freeze — metadata only, no scoring.

Exact command:
  python3 scripts/nfl/freeze_nfl_t5155u_market_arm.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.cohort_enforcement import OutcomeReadSpy  # noqa: E402
from src.services.nfl_t5107u.market_arm_freeze import (  # noqa: E402
    MarketArmFreezeRefuse,
    run_market_arm_freeze,
)


def main() -> int:
    spy = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
    try:
        result = run_market_arm_freeze(root=ROOT, outcome_loader=spy, finalize=True)
    except MarketArmFreezeRefuse as exc:
        print(json.dumps({"ok": False, "error": str(exc), "scoring": None}, indent=2))
        return 1
    payload = result["payload"]
    print(
        json.dumps(
            {
                "ok": True,
                "n": result["n"],
                "bytes_sha256": result["bytes_sha256"],
                "identity_sha256": result["identity_sha256"],
                "one_book_n": payload["intersection"]["one_book_n"],
                "missing_n": payload["intersection"]["missing_n"],
                "n_by_season": payload["intersection"]["n_by_season"],
                "dest": result["dest"],
                "outcome_loader_reads": result["outcome_loader_reads"],
                "scoring": None,
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
