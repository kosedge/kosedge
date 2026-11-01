#!/usr/bin/env python3
"""t5107u offline forecast builder / manifest seal (CERT=0, no EXEC score).

Examples (from repo root):

  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_forecast_builder_t5107u.py --seal-manifest

  PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_forecast_builder_t5107u.py \\
    --targets path/to/targets.json --output data/ops/nfl-forecast-builder-t5107u/forecasts.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.builder import BuilderRefuse, build_forecasts  # noqa: E402
from src.services.nfl_t5107u.evaluator import EvalRefuse, freeze_forecast_cohort  # noqa: E402
from src.services.nfl_t5107u.manifest import DEFAULT_PATH, seal_frozen_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal-manifest", action="store_true", help="Seal FROZEN_MANIFEST and exit")
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--targets", type=Path, help="JSON list of target games (DEV 2020–21 unless sealed)")
    parser.add_argument("--history", type=Path, help="JSON list of prior scored games")
    parser.add_argument("--archived-if", type=Path, help="JSON map of archived IF mus")
    parser.add_argument("--output", type=Path, help="Forecast JSON output")
    parser.add_argument("--allow-eval-generation", action="store_true")
    parser.add_argument("--frozen-manifest-sealed", action="store_true")
    parser.add_argument("--score", action="store_true", help="Refused: EXEC scoring is not authorized")
    args = parser.parse_args(argv)

    if args.score:
        print("REFUSED: EXEC scoring is not authorized in this package (G7).", file=sys.stderr)
        return 2

    if args.seal_manifest:
        payload = seal_frozen_manifest(args.manifest_path)
        print(
            json.dumps(
                {
                    "path": payload["_path"],
                    "manifest_sha256": payload["manifest_sha256"],
                    "eval_generation": payload["eval_generation"],
                    "exec_scoring": payload["exec_scoring"],
                    "fit_policy": payload["fit_policy"]["fit_policy"],
                },
                indent=2,
            )
        )
        return 0

    if not args.targets or not args.output:
        parser.error("either --seal-manifest or both --targets and --output are required")

    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    history = json.loads(args.history.read_text(encoding="utf-8")) if args.history else []
    archived = json.loads(args.archived_if.read_text(encoding="utf-8")) if args.archived_if else {}
    try:
        payload = build_forecasts(
            targets,
            history=history,
            archived_if=archived,
            allow_eval_generation=args.allow_eval_generation,
            frozen_manifest_sealed=args.frozen_manifest_sealed,
        )
        frozen = freeze_forecast_cohort(payload)
        payload["frozen_cohort"] = frozen.as_dict()
    except (BuilderRefuse, EvalRefuse) as exc:
        print(json.dumps({"refused": True, "detail": str(exc)}, indent=2))
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "forecast_n": len(payload["forecasts"]),
                "forecast_sha256": frozen.forecast_sha256,
                "cohort_sha256": frozen.cohort_sha256,
                "eval": payload["eval"],
                "scoring": payload["scoring"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
