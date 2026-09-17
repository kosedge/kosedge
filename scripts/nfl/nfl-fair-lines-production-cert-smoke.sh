#!/usr/bin/env bash
# NFL Fair Lines PRODUCTION-CERT smoke — Product track (Ryan 2026-09-17).
# Source-lock only. Does not remat, invent numbers, flip public flags,
# CLEAR a market, or touch DFS / Line Curve / CFB.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PUB="${ROOT}/apps/web/lib/cfb-edge-board-public.ts"
API="${ROOT}/apps/web/app/api/nfl/fair-lines/route.ts"
PAGE="${ROOT}/apps/web/app/(pro)/pro/nfl/fair-lines/page.tsx"
PACKET="${ROOT}/docs/ops/NFL_FAIR_LINES_PRODUCTION_CERT_PRODUCT_2026-09-17.md"
RECEIPT="${ROOT}/data/ops/nfl-fair-lines-production-cert-product-20260917.md"
MACHINE="${ROOT}/data/ops/nfl-fair-lines-production-cert-product-20260917/packet.json"

pass=0
fail=0

ok() {
  echo "PASS  $1"
  pass=$((pass + 1))
}

bad() {
  echo "FAIL  $1"
  fail=$((fail + 1))
}

has() {
  local file="$1"
  local needle="$2"
  local label="$3"
  if grep -q -- "$needle" "$file"; then
    ok "$label"
  else
    bad "$label (missing '${needle}' in ${file#"$ROOT/"})"
  fi
}

absent() {
  local file="$1"
  local needle="$2"
  local label="$3"
  if grep -q -- "$needle" "$file"; then
    bad "$label (found '${needle}' in ${file#"$ROOT/"})"
  else
    ok "$label"
  fi
}

echo "NFL Fair Lines PRODUCTION-CERT Product smoke (source-lock, public stays dark)"

has "$PUB" "NFL_EDGE_BOARD_PUBLIC_ENABLED = false" "NFL public flag false"
has "$PUB" "CFB_EDGE_BOARD_PUBLIC_ENABLED = false" "CFB public flag false"
has "$PUB" "NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED = false" "spread gate false"
has "$PUB" "NFL_FAIR_LINES_PUBLIC_ML_ENABLED = false" "ml gate false"
has "$PUB" "NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED = false" "total gate false"
has "$PUB" "NFL_FAIR_LINES_PLAY_ENABLED = false" "PLAY suppressed"
has "$PUB" "NFL_FAIR_LINES_KELLY_ENABLED = false" "Kelly suppressed"
has "$PUB" "NFL_FAIR_LINES_CERTIFIED_RUN_ID: string | null = null" "certified run_id unbound"
has "$PUB" "NFL_FAIR_LINES_CERTIFIED_SHA256: string | null = null" "certified sha256 unbound"
has "$PUB" "bindNflFairLinesCertifiedRun" "cert bind helper present"
absent "$PUB" "NFL_EDGE_BOARD_PUBLIC_ENABLED = true" "NFL public not flipped"
absent "$PUB" "CFB_EDGE_BOARD_PUBLIC_ENABLED = true" "CFB public not flipped"
absent "$PUB" "NFL_FAIR_LINES_PLAY_ENABLED = true" "PLAY not flipped"
absent "$PUB" "NFL_FAIR_LINES_KELLY_ENABLED = true" "Kelly not flipped"

has "$API" "isNflFairLinesCustomerSurfaceClosed" "API uses cert-closed helper"
has "$API" "nflEdgeBoardAssembleUnavailablePayload" "API fail-closes empty"
has "$PAGE" "isNflFairLinesCustomerSurfaceClosed" "page uses cert-closed helper"
has "$PAGE" "FootballNumbersUnavailable" "page keeps Coming soon chrome"
has "$PAGE" "Coming soon" "page Coming soon copy"

has "$PACKET" "NO CLEAR" "Product packet NO CLEAR"
has "$PACKET" "Rollback" "Product packet rollback"
has "$RECEIPT" "Coming soon" "ops receipt Coming soon"
has "$MACHINE" "\"NO_CLEAR\"" "machine packet NO_CLEAR"
has "$MACHINE" "\"cos\": \"\"" "CoS approver empty"
has "$MACHINE" "\"ryan\": \"\"" "Ryan approver empty"

if [[ "$fail" -ne 0 ]]; then
  echo "PRODUCTION-CERT Product smoke failed: ${fail} check(s). Public must stay dark."
  exit 1
fi

echo "All ${pass} PRODUCTION-CERT Product smoke checks passed. Public still false."
