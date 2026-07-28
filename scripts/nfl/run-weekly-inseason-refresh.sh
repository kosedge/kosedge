#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEASONS="${SEASONS:-2026}"
WEEK="${WEEK:-}"
MODEL_SERVICE_URL="${MODEL_SERVICE_URL:-http://127.0.0.1:8000}"
MODEL_VERSION="${MODEL_VERSION:-nfl-v1.5-matchup-sim}"

echo "[weekly] Refreshing owned NFL tables (seasons=${SEASONS} week=${WEEK:-all})"
(
  cd "${ROOT_DIR}/services/data-platform-nfl"
  if [[ -n "${WEEK}" ]]; then
    PYTHONPATH=./src python3 -m data_platform_nfl.cli \
      --seasons "${SEASONS}" \
      --week "${WEEK}" \
      --run-launch-hardening \
      --backup-export-dir "${ROOT_DIR}/data/ops"
  else
    PYTHONPATH=./src python3 -m data_platform_nfl.cli \
      --seasons "${SEASONS}" \
      --run-launch-hardening \
      --backup-export-dir "${ROOT_DIR}/data/ops"
  fi
)

echo "[weekly] Running simulation hardening cycle"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-launch-hardening?model_version=${MODEL_VERSION}&days_ahead=14&outcomes_lookback_days=90&backtest_lookback_days=300&tuning_lookback_days=300&simulations=6000"

echo "[weekly] Trigger complete"
