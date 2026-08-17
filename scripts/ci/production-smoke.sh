#!/usr/bin/env bash
# Production smoke — Vercel (www) + Railway (model-service) must both answer.
# used_in_spread / KEI are not flipped here; this only proves the subscription
# surfaces are reachable after a deploy-vercel ship.
set -euo pipefail

WEB_BASE="${WEB_BASE:-https://www.kosedge.com}"
MODEL_BASE="${MODEL_BASE:-https://model-service-production-e253.up.railway.app}"
ATTEMPTS="${ATTEMPTS:-12}"
SLEEP_SECS="${SLEEP_SECS:-20}"

pass=0
fail=0

check() {
  local name="$1"
  local url="$2"
  local needle="${3:-}"
  local code body
  code="$(curl -sS -o /tmp/kosedge-smoke-body.txt -w "%{http_code}" --max-time 30 "$url" || echo "000")"
  body="$(cat /tmp/kosedge-smoke-body.txt 2>/dev/null || true)"
  if [[ "$code" != "200" ]]; then
    echo "FAIL  $name  HTTP $code  $url"
    fail=$((fail + 1))
    return
  fi
  if [[ -n "$needle" ]] && ! grep -qi -- "$needle" /tmp/kosedge-smoke-body.txt; then
    echo "FAIL  $name  HTTP 200 but missing '${needle}'  $url"
    fail=$((fail + 1))
    return
  fi
  echo "PASS  $name  HTTP $code"
  pass=$((pass + 1))
}

echo "Smoking ${WEB_BASE} + ${MODEL_BASE} (up to ${ATTEMPTS} attempts)..."

for i in $(seq 1 "$ATTEMPTS"); do
  pass=0
  fail=0
  echo "--- attempt ${i}/${ATTEMPTS} ---"
  check "web ping" "${WEB_BASE}/api/ping"
  check "cfb overview" "${WEB_BASE}/pro/cfb/overview" "Start here"
  check "cfb slate" "${WEB_BASE}/pro/cfb/slate" "Official slate"
  check "cfb model" "${WEB_BASE}/pro/cfb/model" "used_in_spread"
  check "cfb project-game" "${WEB_BASE}/pro/cfb/project-game" "Project Game"
  check "cfb projections" "${WEB_BASE}/pro/cfb/projections" "N=10000"
  check "cfb teams" "${WEB_BASE}/pro/cfb/teams" "136"
  check "cfb previews" "${WEB_BASE}/pro/cfb/previews" "team previews"
  check "cfb conferences" "${WEB_BASE}/pro/cfb/conferences" "conference previews"
  check "edge-board cfb" "${WEB_BASE}/edge-board/cfb" "Edge Board"
  check "railway health" "${MODEL_BASE}/health" "ok"
  check "cfb engine status" "${MODEL_BASE}/cfb/season-engine/status?season=2026&as_of_week=1&demo=true" "engine_version"

  if [[ "$fail" -eq 0 ]]; then
    echo "All ${pass} checks passed."
    exit 0
  fi
  if [[ "$i" -lt "$ATTEMPTS" ]]; then
    echo "Waiting ${SLEEP_SECS}s for Vercel/Railway to catch up..."
    sleep "$SLEEP_SECS"
  fi
done

echo "Production smoke failed: ${fail} check(s) still red after ${ATTEMPTS} attempts."
exit 1
