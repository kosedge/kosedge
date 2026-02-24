#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"

PORTS=(3000 3001 3002 3003)

echo "==> Killing dev servers on ports: ${PORTS[*]}"
for p in "${PORTS[@]}"; do
  # lsof returns nothing if no process; xargs -r avoids running kill with empty input
  lsof -ti "tcp:${p}" | xargs -r kill -9 || true
done

echo "==> Removing Next dev lock + caches"
rm -f "$WEB_DIR/.next/dev/lock" || true
rm -rf "$WEB_DIR/.next" "$WEB_DIR/.turbo" || true

echo "==> Starting Next dev (apps/web)"
cd "$WEB_DIR"
pnpm dev
