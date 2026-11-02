#!/usr/bin/env python3
"""t5157u — R5-HISTORY-ID identity projection + completed Q2/candidate (CERT=0).

Does not regenerate IF496. Does not overwrite t5155u HOLD artifacts.
Does not run Phase2 scoring. No network / odds / paid.

  PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_history_id_t5157u.py
  PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_history_id_t5157u.py --score
      → refused (zero target labels)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.r5_history_id import (  # noqa: E402
    COS_ORDER_A,
    IF_FORECASTS_SHA256,
    OWNER_CLEAR,
    PATH_ID,
    R5_HISTORY_ID,
    TargetScoringRefuse,
    refuse_phase2_score,
    refuse_target_scoring,
    run_history_id,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", action="store_true", help="Refused: no Phase2 scoring")
    parser.add_argument("--eval", action="store_true", help="Refused: not EVAL")
    parser.add_argument("--load-targets", action="store_true", help="Refused")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    if args.score or args.eval or args.load_targets:
        try:
            refuse_target_scoring()
        except TargetScoringRefuse as exc:
            result = refuse_phase2_score()
            result["detail"] = str(exc)
            print(json.dumps(result, indent=2))
            return 2

    bundle = run_history_id(root=ROOT, write=not args.no_write)
    completed = bundle["FORECASTS_DEV_R5_496_Q2_COMPLETED"]
    stop = bundle["STOP_FOR_COS_B"]
    prov = bundle["JOIN_PROVENANCE"]
    print(
        json.dumps(
            {
                "path_id": PATH_ID,
                "owner_clear": OWNER_CLEAR,
                "r5_history_id": R5_HISTORY_ID,
                "cos_order_a": COS_ORDER_A,
                "n_reg_2013_2019": prov["pbp_2013_2019"]["n_reg"],
                "n_post_2013_2019": prov["pbp_2013_2019"]["n_post"],
                "n_unmatched": prov["n_unmatched"],
                "n_conflict": prov["n_conflict"],
                "n_forecasts": completed.get("n_forecasts"),
                "n_q2_finite": completed.get("n_q2_finite"),
                "n_candidate_finite": completed.get("n_candidate_finite"),
                "if_forecasts_sha256": IF_FORECASTS_SHA256,
                "if_regenerated": False,
                "hold_q2": stop["hold_q2"],
                "stop": stop["stop"],
                "status": stop["status"],
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
