#!/usr/bin/env bash
# Copy repo-root infra/db SQL into the Railway/Docker context.
# `railway up services/model-service --path-as-root` never sees infra/ at repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/infra/db"
DST="$ROOT/services/model-service/infra/db"
if [[ ! -d "$SRC" ]]; then
  echo "missing source migrations dir: $SRC" >&2
  exit 1
fi
mkdir -p "$DST"
# Replace staged copy so deletes in repo-root propagate into the image context.
find "$DST" -mindepth 1 -maxdepth 1 -type f -name '*.sql' -delete 2>/dev/null || true
cp -f "$SRC"/*.sql "$DST/"
count="$(find "$DST" -maxdepth 1 -type f -name '*.sql' | wc -l | tr -d ' ')"
echo "staged ${count} SQL migration(s) -> $DST"
