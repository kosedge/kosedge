#!/usr/bin/env bash
set -euo pipefail

MODEL_SERVICE_URL="${MODEL_SERVICE_URL:-http://127.0.0.1:8000}"
MODEL_VERSION="${MODEL_VERSION:-nfl-v1.5-matchup-sim}"
DAYS_AHEAD="${DAYS_AHEAD:-7}"
OUTCOMES_LOOKBACK_DAYS="${OUTCOMES_LOOKBACK_DAYS:-45}"

echo "[daily] Triggering launch hardening cycle for market refresh"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-launch-hardening?model_version=${MODEL_VERSION}&days_ahead=${DAYS_AHEAD}&outcomes_lookback_days=${OUTCOMES_LOOKBACK_DAYS}&simulations=5000&backtest_lookback_days=240&tuning_lookback_days=240"

echo "[daily] Trigger complete"
