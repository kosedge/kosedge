#!/usr/bin/env python3
"""t5155u / t5160u Phase-2 one-exec (CERT=0).

Loads committed FORECASTS sha 96d3aa6f. Never regenerates.
Default: refuse target labels. Unbound --score refused (0 reads).
``--score --cos-bind FILE`` verifies pins + exclusive claim, then the
real loader once — only after a verified claimed hash-matching bind.
Env flags cannot authorize real labels. Q2/candidate COMPLETED pins.

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
    ALEX_RETURN_T5157U_SHA8,
    COS_ACCEPT_RETURN_FIX_SHA8,
    COS_ORDER_T5157U_SHA8,
    FORECASTS_SHA256,
    Phase2OneExecRefuse,
    run_phase2_one_exec,
)


def _refuse_unbound(detail: str) -> int:
    print(
        json.dumps(
            {
                "refused": True,
                "detail": detail,
                "outcome_loader_reads": 0,
                "cos_order_t5157u_sha8": COS_ORDER_T5157U_SHA8,
                "alex_return_t5157u_sha8": ALEX_RETURN_T5157U_SHA8,
                "cos_accept_return_fix_sha8": COS_ACCEPT_RETURN_FIX_SHA8,
                "forecasts_sha256": FORECASTS_SHA256,
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", action="store_true", help="Requires --cos-bind <file>")
    parser.add_argument("--cos-bind", metavar="FILE", help="One-exec bind record to verify+claim")
    parser.add_argument("--eval", action="store_true", help="Refused: not EVAL")
    parser.add_argument("--load-targets", action="store_true", help="Refused: Alex re-PREFLIGHT")
    args = parser.parse_args(argv)
    if args.eval or args.load_targets:
        return _refuse_unbound("no Cos bind / live --score until ordered — --eval/--load-targets refused")
    if args.score and not args.cos_bind:
        return _refuse_unbound("unbound --score refused — 0 reads")
    if args.cos_bind and not args.score:
        return _refuse_unbound("--cos-bind requires --score")
    if args.score and args.cos_bind:
        try:
            receipt = run_phase2_one_exec(
                root=ROOT,
                cos_bind_path=Path(args.cos_bind),
                score_flag=True,
                write=True,
            )
        except Phase2OneExecRefuse as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "verified": False,
                        "outcome_loader_reads": 0,
                        "cert_candidate": 0,
                    },
                    indent=2,
                )
            )
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
                    "runner_code_sha256": receipt["runner_code_sha256"],
                    "q2": receipt["q2"],
                    "cos_bind": receipt["cos_bind"],
                    "cert_candidate": 0,
                },
                indent=2,
            )
        )
        return 0
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
                "runner_code_sha256": receipt["runner_code_sha256"],
                "q2": receipt["q2"],
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
