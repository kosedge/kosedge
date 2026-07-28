#!/usr/bin/env bash
set -euo pipefail

MODEL_SERVICE_URL="${MODEL_SERVICE_URL:-http://127.0.0.1:8000}"
MODEL_VERSION="${MODEL_VERSION:-nfl-v1.5-matchup-sim}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-120}"

echo "[postweek] Pulling outcomes"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/pull-nfl-outcomes?days_back=${LOOKBACK_DAYS}" >/dev/null

echo "[postweek] Materializing market history"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/materialize-nfl-market-history?lookback_days=${LOOKBACK_DAYS}" >/dev/null

echo "[postweek] Running CLV attribution"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-clv-attribution?lookback_days=${LOOKBACK_DAYS}&model_version=${MODEL_VERSION}" >/dev/null

echo "[postweek] Running quality grading"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-quality-grading?lookback_days=${LOOKBACK_DAYS}&model_version=${MODEL_VERSION}" >/dev/null

echo "[postweek] Running walkforward backtest"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-walkforward-backtest?model_version=${MODEL_VERSION}&lookback_days=300&training_days=56&step_days=7&apply_calibration=true" >/dev/null

echo "[postweek] Running framework tuning + drift"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-framework-tuning?model_version=${MODEL_VERSION}&lookback_days=300&training_days=56&step_days=7&max_candidates=180" >/dev/null
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-decomposition-drift?model_version=${MODEL_VERSION}&lookback_days=140&baseline_weeks=4" >/dev/null

echo "[postweek] Completed grading triggers"
