#!/usr/bin/env bash
# Ensure model-service has a data_platform_nfl package for Docker/Railway builds.
#
# Canonical deploy copy: services/model-service/data_platform_nfl
# (richer than services/data-platform-nfl — includes coach_aggression,
# personnel_efficiency, projection_actuals, etc.)
#
# NEVER rm -rf the vendored package. NEVER clobber an existing vendored tree
# with the thinner monorepo source. Only seed when the destination is missing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/services/data-platform-nfl/src/data_platform_nfl"
DST="$ROOT/services/model-service/data_platform_nfl"

if [[ -d "$DST" ]] && [[ -n "$(ls -A "$DST" 2>/dev/null || true)" ]]; then
  echo "Preserved existing services/model-service/data_platform_nfl (no clobber)"
  exit 0
fi

if [[ ! -d "$SRC" ]]; then
  echo "Missing source package to seed vendored DP: $SRC" >&2
  exit 1
fi

mkdir -p "$DST"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude '__pycache__/' --exclude '*.pyc' "$SRC/" "$DST/"
else
  cp -R "$SRC"/. "$DST"/
fi
echo "Seeded missing data_platform_nfl -> services/model-service/data_platform_nfl"
