#!/usr/bin/env python3
"""t5137u — persist omitted matched72 DEV comparison fields. Not EVAL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.dev_research_matched72 import (  # noqa: E402
    DEFAULT_DEST,
    build_matched72_dev_research_record,
)


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST
    record = build_matched72_dev_research_record(dest=dest)
    print(
        json.dumps(
            {
                "status": "DEV_RESEARCH",
                "reporting": record["reporting"],
                "metric_split": record["metric_split"],
                "split": record["split"],
                "cohort": record["cohort"],
                "n": record["n"],
                "mae_challenger": record["mae_challenger"],
                "mae_if": record["mae_if"],
                "mae_market": record["mae_market"],
                "mean_signed_diff_vs_if": record["mean_signed_diff_vs_if"],
                "mean_signed_diff_vs_market": record["mean_signed_diff_vs_market"],
                "eval_invoked": record["eval_invoked"],
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
