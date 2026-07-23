#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/services/data-platform-nfl/src/data_platform_nfl"
DST="$ROOT/services/model-service/data_platform_nfl"
rm -rf "$DST"
cp -R "$SRC" "$DST"
echo "Synced data_platform_nfl -> services/model-service/data_platform_nfl"
