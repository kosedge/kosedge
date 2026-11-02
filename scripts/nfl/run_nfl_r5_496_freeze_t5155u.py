#!/usr/bin/env python3
"""t5155u — opt-in DEV_R5_496 Phase 1 FREEZE (CERT=0).

Identity → 27-input validate → IF produce-μ → Q2 HOLD-or-forecast → 437 compare.
STOP before any target scoring loader / diagnostic execution.

Preserves earlier runners/forecasts/results. NOT EVAL / production / market-edge / GREEN.

  PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_496_freeze_t5155u.py
  PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_496_freeze_t5155u.py --score
      → refused (zero target labels)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.r5_496_freeze import (  # noqa: E402
    COS_ORDER_SHA8,
    OWNER_CLEAR_SHA8,
    PATH_ID,
    PROFILE_FEATURE_RECON_REG496,
    TargetScoringRefuse,
    expected_profile_ids,
    refuse_target_scoring,
    run_phase1_freeze,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--score",
        action="store_true",
        help="Refused: Phase 1 cannot load target scoring labels",
    )
    parser.add_argument("--eval", action="store_true", help="Refused: not EVAL")
    parser.add_argument(
        "--load-targets",
        action="store_true",
        help="Refused: STOP for Alex preflight + Cos bind",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Run freeze without writing artifacts",
    )
    args = parser.parse_args(argv)

    if args.score or args.eval or args.load_targets:
        ids = expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT)
        try:
            result = refuse_target_scoring(candidate_ids=ids, root=ROOT)
        except TargetScoringRefuse as exc:
            print(json.dumps({"refused": True, "detail": str(exc), "target_labels": 0}, indent=2))
            return 2
        print(
            json.dumps(
                {
                    "refused": True,
                    "path_id": PATH_ID,
                    "detail": result["reason"],
                    "outcome_loader_reads": result["outcome_loader_reads"],
                    "target_labels_loaded": result["target_labels_loaded"],
                    "stop": result["stop"],
                    "cert_candidate": 0,
                },
                indent=2,
            )
        )
        return 2

    bundle = run_phase1_freeze(root=ROOT, write=not args.no_write, compare_old_if=True)
    forecasts = bundle["FORECASTS_DEV_R5_496"]
    compare = bundle["COMPARE_437"]
    print(
        json.dumps(
            {
                "path_id": PATH_ID,
                "owner_clear_sha8": OWNER_CLEAR_SHA8,
                "cos_order_sha8": COS_ORDER_SHA8,
                "n_forecasts": forecasts["n_forecasts"],
                "n_if_finite": forecasts["n_if_finite"],
                "n_q2_hold": forecasts["n_q2_hold"],
                "n_candidate_finite": forecasts["n_candidate_finite"],
                "identity_sha256": bundle["IDENTITY_MANIFEST"]["identity_sha256"],
                "n_identical_27": compare.get("input_compare", {}).get("n_identical_27"),
                "n_replayed": compare.get("n_replayed_within_tol"),
                "n_blocker": compare.get("n_blocker", 0),
                "stop": bundle["STOP_AWAITING_ALEX_PREFLIGHT_AND_COS_BIND"]["stop"],
                "written": bundle.get("written"),
                "cert_candidate": 0,
                "eval": None,
                "scoring": None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
