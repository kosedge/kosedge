#!/usr/bin/env bash
# One-button deploy: model-service API + worker + beat on Railway (brave-art).
#
# Usage (from repo root):
#   bash scripts/deploy-railway-model-service.sh
#   bash scripts/deploy-railway-model-service.sh --wait
#
# Requirements: railway CLI logged in, linked project OR RAILWAY_TOKEN set.
# Always uses --path-as-root so Dockerfile is found (never monorepo-root build).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.volta/bin:/usr/local/bin:${PATH}"

PROJECT_ID="${RAILWAY_PROJECT_ID:-da3d68f8-d925-462f-b262-c4ef3e488245}"
ENV_ID="${RAILWAY_ENVIRONMENT_ID:-4bf00465-0220-4764-8b3b-e7adce18ca64}"
WAIT=0
for arg in "$@"; do
  case "$arg" in
    --wait) WAIT=1 ;;
  esac
done

if ! command -v railway >/dev/null 2>&1; then
  echo "railway CLI not found. Install: npm i -g @railway/cli" >&2
  exit 1
fi

if [[ -f scripts/nfl/sync-model-service-vendor.sh ]]; then
  bash scripts/nfl/sync-model-service-vendor.sh
fi

deploy_one() {
  local service="$1"
  local label="$2"
  echo "==> Deploying ${label} (${service})"
  railway up services/model-service --path-as-root --no-gitignore --detach \
    --project "${PROJECT_ID}" \
    --environment "${ENV_ID}" \
    --service "${service}" \
    -m "one-button ${label} $(git rev-parse --short HEAD 2>/dev/null || echo local)"
}

# Enforce process roles BEFORE image restart (critical).
echo "==> Enforcing PROCESS_TYPE / PORT"
railway variables set PROCESS_TYPE=api --service model-service --project "${PROJECT_ID}" --environment "${ENV_ID}" >/dev/null
railway variables set PORT=8080 --service model-service --project "${PROJECT_ID}" --environment "${ENV_ID}" >/dev/null || true
railway variables set PROCESS_TYPE=worker --service model-service-worker --project "${PROJECT_ID}" --environment "${ENV_ID}" >/dev/null
railway variables set PROCESS_TYPE=beat --service model-service-beat --project "${PROJECT_ID}" --environment "${ENV_ID}" >/dev/null

deploy_one "model-service" "api"
deploy_one "model-service-worker" "worker"
deploy_one "model-service-beat" "beat"

echo "==> Deploys queued"
if [[ "$WAIT" -eq 1 ]]; then
  echo "Waiting for API health..."
  for i in $(seq 1 60); do
    if curl -fsS -m 10 https://model-service-production-e253.up.railway.app/health >/dev/null 2>&1; then
      echo "API healthy"
      curl -sS -m 10 https://model-service-production-e253.up.railway.app/health
      echo
      exit 0
    fi
    sleep 10
  done
  echo "Timed out waiting for /health" >&2
  exit 1
fi

echo "Run with --wait to block until /health is 200."
echo "Season data refresh is Celery beat (every 5–10 min) — not this deploy."
