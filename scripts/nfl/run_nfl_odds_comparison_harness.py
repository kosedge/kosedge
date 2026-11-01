#!/usr/bin/env python3
"""Run the synthetic NFL odds comparison harness (CERT=0, DRAFT≠merge).

Example (from repo root):

  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_odds_comparison_harness.py \\
    --forecasts data/ops/nfl-odds-comparison-harness-t5100u/fixtures/example-forecasts.json \\
    --odds-manifest data/ops/nfl-odds-comparison-harness-t5100u/fixtures/example-odds-manifest.json \\
    --output data/ops/nfl-odds-comparison-harness-t5100u/example-output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_odds_comparison_harness import (  # noqa: E402
    HarnessRefusal,
    run_comparison_files,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecasts", required=True, type=Path, help="Frozen synthetic forecast JSON")
    parser.add_argument("--odds-manifest", required=True, type=Path, help="Matching synthetic owned-odds manifest")
    parser.add_argument("--output", required=True, type=Path, help="Comparison report JSON path")
    args = parser.parse_args(argv)

    try:
        report = run_comparison_files(args.forecasts, args.odds_manifest)
    except HarnessRefusal as exc:
        payload = exc.as_dict()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 2

    dest = write_report(report, args.output)
    summary = {
        "output": str(dest),
        "comparison_n": len(report.comparisons),
        "excluded_n": len(report.excluded),
        "reason_tallies": report.reason_tallies,
        "cert_candidate": report.cert_candidate,
        "refused": report.refused,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
