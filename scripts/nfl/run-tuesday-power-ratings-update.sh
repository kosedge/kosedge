#!/usr/bin/env bash
# Tuesday NFL Power Ratings desk publish (ET).
#
# Usage:
#   ./scripts/nfl/run-tuesday-power-ratings-update.sh
#   WEEK=1 ./scripts/nfl/run-tuesday-power-ratings-update.sh
#   WEEK=2 ./scripts/nfl/run-tuesday-power-ratings-update.sh --dry-run
#
# Preseason (default WEEK=0): writes initial Model PR snapshot; no shrinkage.
# In-season: Bayesian shrink vs prior Tuesday publish, full audit trail.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEASON="${SEASON:-2026}"
WEEK="${WEEK:-0}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python3}"
EXTRA_ARGS=()

for arg in "$@"; do
  case "${arg}" in
    --dry-run|-n) EXTRA_ARGS+=(--dry-run) ;;
    --help|-h)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      exit 2
      ;;
  esac
done

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" scripts/nfl/tuesday_power_ratings_update.py \
  --season "${SEASON}" \
  --week "${WEEK}" \
  "${EXTRA_ARGS[@]}"
