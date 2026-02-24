#!/usr/bin/env bash
set -euo pipefail

echo "==> Killing anything on port 3000"
lsof -ti tcp:3000 | xargs -r kill -9 || true

echo "==> Clearing Next caches"
rm -rf apps/web/.next apps/web/.turbo

echo "==> Starting web on :3000"
pnpm -C apps/web dev -- --port 3000
