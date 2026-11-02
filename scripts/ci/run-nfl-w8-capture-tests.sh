#!/usr/bin/env bash
# IMV rerun pointer for draft #640 W8 prospective capture.
# Synthetic fixtures only. Does not call The Odds API.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/services/model-service"
export PYTHONPATH="."
python3 -m pytest tests/test_nfl_w8_capture.py -q
