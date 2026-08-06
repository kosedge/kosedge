#!/usr/bin/env bash
# Generate NFL + CFB historical calibration report artifacts from the live proof lake.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/model-service"

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src:$(pwd)"

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

from src.services.proof_layer.calibration_report import generate_calibration_report

report_dir = Path("data/ops/calibration_reports")
report_dir.mkdir(parents=True, exist_ok=True)

for sport in ("nfl", "cfb"):
    out = generate_calibration_report(sport=sport, write_artifact=True, report_dir=report_dir)
    print(f"\n=== {sport.upper()} ===")
    print(out.get("summary_text", ""))
    print(f"artifact: {out.get('artifact_path')}")
    print(f"honesty: {out.get('honesty_flags')}")

print("\nDone.")
PY
