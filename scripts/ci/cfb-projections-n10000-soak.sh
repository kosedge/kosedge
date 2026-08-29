#!/usr/bin/env bash
# CFB projections N=10000 soak — Desk OS item D.
#
# NOT merge-blocking. NOT part of Production Smoke / deploy-vercel ship bar.
# Soak only: scheduled + workflow_dispatch (.github/workflows/cfb-projections-soak.yml).
# N is unchanged (still asserts N=10000). Do not retune N here; ticket on failure.
#
# Why moved: intermittent CFB page grain was failing NFL Desk OS / deploy-vercel
# smoke while Railway + the rest of the CFB suite were healthy.
set -euo pipefail

WEB_BASE="${WEB_BASE:-https://www.kosedge.com}"
ATTEMPTS="${ATTEMPTS:-8}"
SLEEP_SECS="${SLEEP_SECS:-20}"
# soak/slow marker — this script is the soak job entrypoint (not pytest.skip).
SOAK_MARKER="soak/slow"

pass=0
fail=0

check() {
  local name="$1"
  local url="$2"
  local needle="${3:-}"
  local code
  code="$(curl -sS -o /tmp/kosedge-cfb-soak-body.txt -w "%{http_code}" --max-time 30 "$url" || echo "000")"
  if [[ "$code" != "200" ]]; then
    echo "FAIL  $name  HTTP $code  $url"
    fail=$((fail + 1))
    return
  fi
  if [[ -n "$needle" ]] && ! grep -qi -- "$needle" /tmp/kosedge-cfb-soak-body.txt; then
    echo "FAIL  $name  HTTP 200 but missing '${needle}'  $url"
    fail=$((fail + 1))
    return
  fi
  echo "PASS  $name  HTTP $code"
  pass=$((pass + 1))
}

echo "CFB projections N=10000 soak (${SOAK_MARKER}) against ${WEB_BASE}"
echo "Not merge-blocking — see .github/workflows/cfb-projections-soak.yml"

for i in $(seq 1 "$ATTEMPTS"); do
  pass=0
  fail=0
  echo "--- attempt ${i}/${ATTEMPTS} ---"
  check "cfb projections N=10000" "${WEB_BASE}/pro/cfb/projections" "N=10000"
  if [[ "$fail" -eq 0 ]]; then
    echo "Soak passed (${pass} checks)."
    exit 0
  fi
  if [[ "$i" -lt "$ATTEMPTS" ]]; then
    echo "Waiting ${SLEEP_SECS}s..."
    sleep "$SLEEP_SECS"
  fi
done

echo "CFB projections N=10000 soak failed after ${ATTEMPTS} attempts — open a ticket; do not fail Desk OS / deploy-vercel."
exit 1
