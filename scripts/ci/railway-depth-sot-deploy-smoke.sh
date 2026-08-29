#!/usr/bin/env bash
# Post-Railway smoke: e253 must serve DepthSot ops (auth 200/401). 404 = fail.
# Detach upload is not a pass — call this after api is expected live.
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

echo "## DepthSot deploy smoke"
echo "e253_target=${MODEL_BASE}"
echo "api_service_id_expected=${API_SERVICE_ID_EXPECTED}"
echo "project_id=${PROJECT_ID}"
echo "expected_sha12=${EXPECTED_SHA12:-unknown}"
echo "routes_mount=services/model-service/src/routes/nfl.py (nfl_router prefix=/nfl) via src.main include_router"
echo "detach_note=railway up --detach only uploads; this smoke requires a ready SHA on e253"

deadline=$((SECONDS + WAIT_SECONDS))
last_code="000"
while (( SECONDS < deadline )); do
  health_json="$(curl -sS -m 15 "${MODEL_BASE}/health" || true)"
  echo "health=${health_json}"

  # OpenAPI route list (depth-sot subset)
  routes="$(
    curl -sS -m 30 "${MODEL_BASE}/openapi.json" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(sorted(p for p in d.get('paths',{}) if 'depth-sot' in p)) or 'NONE')" \
      2>/dev/null || echo 'OPENAPI_FAIL'
  )"
  echo "depth_sot_routes=${routes}"

  auth_code="$(
    curl -sS -m 15 -o /tmp/depth-sot-status.json -w '%{http_code}' \
      -H "x-kosedge-secret: ${SECRET}" \
      "${MODEL_BASE}/nfl/ops/depth-sot/status" || echo err
  )"
  noauth_code="$(
    curl -sS -m 15 -o /tmp/depth-sot-status-noauth.json -w '%{http_code}' \
      "${MODEL_BASE}/nfl/ops/depth-sot/status" || echo err
  )"
  last_code="${auth_code}"
  echo "depth_sot_status auth=${auth_code} noauth=${noauth_code}"

  running_sha="$(
    python3 -c "import json,sys; print((json.loads(sys.argv[1]).get('git_sha') or 'unknown'))" "${health_json}" 2>/dev/null || echo unknown
  )"
  running_svc="$(
    python3 -c "import json,sys; print((json.loads(sys.argv[1]).get('railway_service_id') or 'unknown'))" "${health_json}" 2>/dev/null || echo unknown
  )"
  echo "running_sha=${running_sha} running_railway_service_id=${running_svc}"

  # Pass: authenticated 200 (secret configured) OR 401 (route live, auth enforced).
  # Fail hard on 404 — route not mounted on the host e253 points at.
  if [[ "${auth_code}" == "200" || "${auth_code}" == "401" ]]; then
    if [[ "${auth_code}" == "200" && "${noauth_code}" != "401" && "${noauth_code}" != "403" ]]; then
      echo "FAIL: status returned 200 with secret but noauth was ${noauth_code} (expected 401)" >&2
      exit 1
    fi
    echo "PASS: depth-sot status reachable (auth=${auth_code})"
    echo "summary api_service_id=${running_svc} e253=${MODEL_BASE} running_sha=${running_sha} routes=${routes}"
    exit 0
  fi

  if [[ "${auth_code}" == "404" ]]; then
    echo "still 404 — image on e253 does not mount /nfl/ops/depth-sot yet"
  fi
  sleep "${SLEEP_SECONDS}"
done

echo "FAIL: depth-sot status still HTTP ${last_code} after ${WAIT_SECONDS}s (want 200 or 401, not 404)" >&2
echo "explanation: railway up --detach succeeds on upload; e253 keeps serving the previous SHA until a build finishes and passes /health" >&2
echo "api_service_id_expected=${API_SERVICE_ID_EXPECTED} e253_target=${MODEL_BASE} expected_sha12=${EXPECTED_SHA12:-unknown}" >&2
exit 1
