#!/usr/bin/env python3
"""t5155u RETURN-FIX — Phase-2 one-exec (CERT=0).

Loads committed FORECASTS sha 96d3aa6f. Never regenerates.
Default: refuse target labels (Alex re-PREFLIGHT). --score refused until Cos bind.

  PYTHONPATH=services/model-service python scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.cohort_enforcement import OutcomeReadSpy  # noqa: E402
from src.services.nfl_t5107u.r5_phase2_one_exec import (  # noqa: E402
    COS_ACCEPT_RETURN_FIX_SHA8,
    COS_ORDER_RETURN_FIX_SHA8,
    FORECASTS_SHA256,
    Phase2OneExecRefuse,
    run_phase2_one_exec,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", action="store_true", help="Refused until Cos bind")
    parser.add_argument("--eval", action="store_true", help="Refused: not EVAL")
    parser.add_argument("--load-targets", action="store_true", help="Refused: Alex re-PREFLIGHT")
    args = parser.parse_args(argv)
    if args.score or args.eval or args.load_targets:
        print(
            json.dumps(
                {
                    "refused": True,
                    "detail": "no Cos bind / live --score until Alex re-PREFLIGHT",
                    "outcome_loader_reads": 0,
                    "cos_order_return_fix_sha8": COS_ORDER_RETURN_FIX_SHA8,
                    "cos_accept_return_fix_sha8": COS_ACCEPT_RETURN_FIX_SHA8,
                    "forecasts_sha256": FORECASTS_SHA256,
                    "cert_candidate": 0,
                },
                indent=2,
            )
        )
        return 2
    spy = OutcomeReadSpy(lambda: {"SHOULD_NOT_LOAD": {"home_score": 99}})
    try:
        receipt = run_phase2_one_exec(
            root=ROOT,
            outcome_loader=spy,
            invoke_outcome_after_gates=False,
            write=True,
        )
    except Phase2OneExecRefuse as exc:
        print(json.dumps({"ok": False, "error": str(exc), "verified": False}, indent=2))
        return 1
    if spy.reads != 0:
        print(json.dumps({"ok": False, "error": "default command read targets", "verified": False}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "verified": False,
                "status": receipt["status"],
                "stop": receipt["stop"],
                "forecasts_sha256": receipt["forecasts_sha256"],
                "outcome_loader_reads": receipt["outcome_loader_reads"],
                "q2": receipt["q2"],
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
