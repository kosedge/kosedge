#!/usr/bin/env bash
# Kill everything on port 3000, then start Next.js at http://127.0.0.1:3000
set -e
cd "$(dirname "$0")/.."

echo "Killing processes on port 3000..."
for pid in $(lsof -ti :3000 2>/dev/null); do
  kill -9 "$pid" 2>/dev/null || true
done
# Also kill any orphaned node/next processes that might hold the port
pkill -f "next dev.*3000" 2>/dev/null || true
sleep 2

echo "Starting Next.js at http://127.0.0.1:3000 ..."
exec pnpm --filter @kosedge/web run dev:local
