#!/usr/bin/env bash
# Post-Railway API smoke for DepthSot on e253.
# Detach upload is not a pass. Fail on 404. When INTERNAL_API_SECRET is set,
# require ping=200 + status=200 (401-with-secret = Railway var mismatch).
set -euo pipefail

MODEL_BASE="${MODEL_BASE:-https://model-service-production-e253.up.railway.app}"
MODEL_BASE="${MODEL_BASE%/}"
SECRET="${INTERNAL_API_SECRET:-}"
API_SERVICE_ID_EXPECTED="${RAILWAY_API_SERVICE_ID:-e0c54f94-3ee0-41c0-8081-e96d3e246a4a}"
PROJECT_ID="${RAILWAY_PROJECT_ID_DEFAULT:-da3d68f8-d925-462f-b262-c4ef3e488245}"
EXPECTED_SHA="${EXPECTED_GIT_SHA:-${GITHUB_SHA:-}}"
EXPECTED_SHA12="$(printf '%s' "${EXPECTED_SHA}" | cut -c1-12)"
WAIT_SECONDS="${DEPTH_SOT_SMOKE_WAIT_SECONDS:-300}"
SLEEP_SECONDS="${DEPTH_SOT_SMOKE_SLEEP_SECONDS:-15}"
REQUIRE_AUTH_OK="${DEPTH_SOT_REQUIRE_AUTH_OK:-}"
if [[ -z "${REQUIRE_AUTH_OK}" ]]; then
  if [[ -n "${SECRET}" ]]; then
    REQUIRE_AUTH_OK=1
  else
    REQUIRE_AUTH_OK=0
  fi
fi

echo "## DepthSot deploy smoke"
echo "e253_target=${MODEL_BASE}"
echo "api_service_id_expected=${API_SERVICE_ID_EXPECTED}"
echo "project_id=${PROJECT_ID}"
echo "expected_sha12=${EXPECTED_SHA12:-unknown}"
echo "require_auth_ok=${REQUIRE_AUTH_OK}"
echo "routes_mount=services/model-service/src/routes/nfl.py (nfl_router prefix=/nfl)"
echo "detach_note=railway up --detach only uploads; this smoke requires a ready image on e253"

deadline=$((SECONDS + WAIT_SECONDS))
last_auth="000"
last_ping="000"
while (( SECONDS < deadline )); do
  health_json="$(curl -sS -m 15 "${MODEL_BASE}/health" || true)"
  echo "health=${health_json}"

  routes="$(
    curl -sS -m 30 "${MODEL_BASE}/openapi.json" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(sorted(p for p in d.get('paths',{}) if 'depth-sot' in p)) or 'NONE')" \
      2>/dev/null || echo 'OPENAPI_FAIL'
  )"
  echo "depth_sot_routes=${routes}"

  ping_code="$(
    curl -sS -m 15 -o /tmp/depth-sot-ping.json -w '%{http_code}' \
      -H "x-kosedge-secret: ${SECRET}" \
      "${MODEL_BASE}/nfl/ops/depth-sot/ping" || echo err
  )"
  auth_code="$(
    curl -sS -m 15 -o /tmp/depth-sot-status.json -w '%{http_code}' \
      -H "x-kosedge-secret: ${SECRET}" \
      "${MODEL_BASE}/nfl/ops/depth-sot/status" || echo err
  )"
  noauth_code="$(
    curl -sS -m 15 -o /tmp/depth-sot-status-noauth.json -w '%{http_code}' \
      "${MODEL_BASE}/nfl/ops/depth-sot/status" || echo err
  )"
  last_auth="${auth_code}"
  last_ping="${ping_code}"
  echo "ping_auth=${ping_code} status_auth=${auth_code} status_noauth=${noauth_code}"

  running_sha="$(
    python3 -c "import json,sys; print((json.loads(sys.argv[1]).get('git_sha') or ''))" "${health_json}" 2>/dev/null || true
  )"
  running_svc="$(
    python3 -c "import json,sys; print((json.loads(sys.argv[1]).get('railway_service_id') or ''))" "${health_json}" 2>/dev/null || true
  )"
  echo "running_sha=${running_sha:-null} running_railway_service_id=${running_svc:-null}"

  if [[ "${auth_code}" == "404" || "${ping_code}" == "404" ]]; then
    echo "still 404 — e253 image missing depth-sot ping/status"
    sleep "${SLEEP_SECONDS}"
    continue
  fi

  if [[ "${noauth_code}" != "401" && "${noauth_code}" != "403" ]]; then
    echo "waiting: noauth status=${noauth_code} (want 401)"
    sleep "${SLEEP_SECONDS}"
    continue
  fi

  if [[ "${REQUIRE_AUTH_OK}" == "1" ]]; then
    if [[ "${auth_code}" == "401" ]]; then
      echo "AUTH MISMATCH: status 401 with INTERNAL_API_SECRET set — Railway e0c54f94 var ≠ CI/agent secret" >&2
      # Keep polling in case var is updated mid-wait; do not PASS on 401-with-secret.
      sleep "${SLEEP_SECONDS}"
      continue
    fi
    if [[ "${ping_code}" != "200" || "${auth_code}" != "200" ]]; then
      echo "waiting: want ping=200 status=200 (got ping=${ping_code} status=${auth_code})"
      sleep "${SLEEP_SECONDS}"
      continue
    fi
  else
    # No secret in CI: route presence only (401/200). Prefer not to green-wash auth.
    if [[ "${auth_code}" != "200" && "${auth_code}" != "401" ]]; then
      sleep "${SLEEP_SECONDS}"
      continue
    fi
  fi

  if [[ -z "${running_sha}" || "${running_sha}" == "null" ]]; then
    echo "waiting: /health git_sha still null (bake .deploy-git-sha into image)"
    sleep "${SLEEP_SECONDS}"
    continue
  fi

  if [[ -n "${EXPECTED_SHA12}" && "${running_sha}" != "${EXPECTED_SHA12}" ]]; then
    echo "waiting: running_sha=${running_sha} expected_sha12=${EXPECTED_SHA12}"
    sleep "${SLEEP_SECONDS}"
    continue
  fi

  if [[ -n "${running_svc}" && "${running_svc}" != "${API_SERVICE_ID_EXPECTED}"* ]]; then
    echo "FAIL: railway_service_id=${running_svc} expected prefix ${API_SERVICE_ID_EXPECTED}" >&2
    exit 1
  fi

  echo "PASS: depth-sot live on e253"
  echo "summary api_service_id=${running_svc} e253=${MODEL_BASE} running_sha=${running_sha} ping=${ping_code} status_auth=${auth_code} status_noauth=${noauth_code} routes=${routes}"
  exit 0
done

echo "FAIL: depth-sot smoke timed out after ${WAIT_SECONDS}s (ping=${last_ping} status_auth=${last_auth})" >&2
echo "explanation: upload≠ready; need baked git_sha + matching INTERNAL_API_SECRET on e0c54f94" >&2
echo "api_service_id_expected=${API_SERVICE_ID_EXPECTED} e253_target=${MODEL_BASE} expected_sha12=${EXPECTED_SHA12:-unknown}" >&2
exit 1
