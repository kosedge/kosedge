#!/usr/bin/env python3
"""t5141u R3-DEV-CALIBRATION — freeze / STOP / one diagnostic after Alex GO.

Default: write or verify the isolated pre-fit freeze package and STOP.
Does not fit C2/C3 and does not execute the 2021 diagnostic unless
``--go t5141u-alex-precomp-go`` is supplied (Alex pre-computation GO only).
CERT=0. NOT EVAL. Isolated directory. Parent R2 files are not rewritten.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.r3_dev_calibration import (  # noqa: E402
    ALEX_PRECOMP_GO_TOKEN,
    DEFAULT_DEST,
    ISOLATED_OPS,
    CalibrationRefuse,
    build_pre_fit_freeze_package,
    pre_fit_status,
    run_r3_calibration,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--go",
        default=None,
        help="Alex pre-computation GO token. Omit to STOP before the diagnostic.",
    )
    parser.add_argument("--dest-dir", default=None, help="Override isolated freeze directory")
    parser.add_argument("--dest", default=None, help="Override diagnostic record path")
    args = parser.parse_args()
    dest_dir = Path(args.dest_dir) if args.dest_dir else ISOLATED_OPS

    if args.go is None:
        status = pre_fit_status(dest_dir)
        if not status["freeze_present"]:
            manifest = build_pre_fit_freeze_package(dest_dir)
        else:
            manifest = json.loads((dest_dir / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "status": "STOP_AWAITING_ALEX_PRECOMP_GO",
                    "cert_candidate": 0,
                    "eval": None,
                    "c2_c3_fitted": False,
                    "diagnostic_executed": bool(status["diagnostic_record_present"]),
                    "isolated_dir": str(dest_dir),
                    "freeze_manifest_sha256": manifest.get("file_sha256", {}).get("FREEZE_MANIFEST.json"),
                    "input_pins": manifest.get("input_pins"),
                    "go_token_required": ALEX_PRECOMP_GO_TOKEN,
                    "note": (
                        "Pre-fit hashes frozen. 2021 diagnostic not executed. "
                        "DEV outcomes already consumed. R2-C DATA_COVERAGE_BLOCKED."
                    ),
                },
                indent=2,
            )
        )
        return 0

    try:
        record = run_r3_calibration(
            go=args.go,
            dest=Path(args.dest) if args.dest else (dest_dir / DEFAULT_DEST.name),
            dest_dir=dest_dir,
        )
    except CalibrationRefuse as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc)}, indent=2))
        return 2
    print(
        json.dumps(
            {
                "status": "DEV_RESEARCH",
                "n": record["n"],
                "c3_w": record["c3_selection"]["w"],
                "c3_b": record["c3_selection"]["b"],
                "eval": record["eval"],
                "winner": record["winner"],
                "one_run_claim": record["one_run_claim"],
                "record_sha256": record["record_sha256"],
                "path": record.get("_path"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
