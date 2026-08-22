#!/usr/bin/env bash
# Copy repo-root K/DST publish JSON into the Railway/Docker context.
# `railway up services/model-service --path-as-root` never sees data/ops at repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/data/ops/artifacts"
DST="$ROOT/services/model-service/data/ops/artifacts"
mkdir -p "$DST"
shopt -s nullglob
files=("$SRC"/nfl-kdst-season-*.json)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "no K/DST artifacts in $SRC — worker remat will stay history-only for named K" >&2
  exit 0
fi
cp -f "${files[@]}" "$DST/"
echo "staged ${#files[@]} K/DST artifact(s) -> $DST"
ls -l "$DST"/nfl-kdst-season-*.json
