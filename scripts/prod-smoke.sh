#!/usr/bin/env bash
# Post-deploy smoke checks for www.kosedge.com (and optional base URL).
# Usage: bash scripts/prod-smoke.sh [BASE_URL]
set -euo pipefail

BASE="${1:-https://www.kosedge.com}"
BASE="${BASE%/}"
FAIL=0

body_text_len() {
  python3 -c '
import re, sys
html = sys.stdin.read()
body = re.search(r"<body[^>]*>(.*)</body>", html, re.I | re.S)
b = body.group(1) if body else html
t = re.sub(r"<script[\s\S]*?</script>", " ", b, flags=re.I)
t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
t = re.sub(r"<[^>]+>", " ", t)
t = re.sub(r"\s+", " ", t).strip()
print(len(t))
'
}

check() {
  local path="$1"
  local expect_re="${2:-.}"
  local url="${BASE}${path}"
  local tmp
  tmp="$(mktemp)"
  local code
  code="$(curl -sS -L --max-time 45 -o "$tmp" -w "%{http_code}" "$url" || echo "000")"
  if [[ "$code" != "200" ]]; then
    echo "FAIL  $url  status=$code"
    rm -f "$tmp"
    FAIL=1
    return
  fi
  if ! grep -Eqi "$expect_re" "$tmp"; then
    echo "FAIL  $url  missing content matching /$expect_re/"
    rm -f "$tmp"
    FAIL=1
    return
  fi
  local len
  len="$(body_text_len <"$tmp")"
  rm -f "$tmp"
  if [[ "${len:-0}" -lt 80 ]]; then
    echo "FAIL  $url  body text too short (len=$len) — possible black screen"
    FAIL=1
    return
  fi
  echo "OK    $url  text_len=$len"
}

echo "Smoke base: $BASE"
check "/" "Kos Edge"
check "/pro/nfl/overview" "NFL Overview|Overview"
check "/pro/nfl/slate/today" "Slate|WEEKLY|NFL"
check "/edge-board/nfl" "Edge|NFL|KEI"
check "/api/ping" '"ok"[[:space:]]*:[[:space:]]*true'

logo_brand="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 20 "${BASE}/brand/kosedge-logo.png" || echo 000)"
logo_Brand="$(curl -sS -L -o /dev/null -w "%{http_code}" --max-time 20 "${BASE}/Brand/kosedge-logo.png" || echo 000)"
if [[ "$logo_brand" != "200" ]]; then
  echo "FAIL  /brand/kosedge-logo.png status=$logo_brand"
  FAIL=1
else
  echo "OK    /brand/kosedge-logo.png"
fi
if [[ "$logo_Brand" != "200" ]]; then
  echo "FAIL  /Brand/kosedge-logo.png (follow redirects) status=$logo_Brand"
  FAIL=1
else
  echo "OK    /Brand/kosedge-logo.png (resolved)"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "SMOKE FAILED"
  exit 1
fi
echo "SMOKE PASSED"
