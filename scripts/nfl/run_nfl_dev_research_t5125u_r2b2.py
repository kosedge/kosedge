#!/usr/bin/env python3
"""t5125u R2-B2 — materialize 437-game DEV_RESEARCH cohort. Not EVAL. No claim."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.dev_research_cohort import (  # noqa: E402
    DEFAULT_COHORT_RECORD,
    materialize_dev_research_cohort_437,
)
from src.services.nfl_t5107u.outcome_gate import refuse_overwrite_first_case_record  # noqa: E402


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_COHORT_RECORD
    refuse_overwrite_first_case_record(dest)
    record = materialize_dev_research_cohort_437(dest=dest)
    print(
        json.dumps(
            {
                "status": "DEV_RESEARCH",
                "n": record["n"],
                "dev_reg_sha256": record["dev_reg_sha256"],
                "mae_challenger": record["mae_challenger"],
                "mae_if": record["mae_if"],
                "rmse_challenger": record["rmse_challenger"],
                "bias_challenger": record["bias_challenger"],
                "mean_signed_diff_vs_if": record["mean_signed_diff_vs_if"],
                "market": record["market"]["status"],
                "one_run_claim": record["one_run_claim"],
                "record_sha256": record["record_sha256"],
                "path": str(dest),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
