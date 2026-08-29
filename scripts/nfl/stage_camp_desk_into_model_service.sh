#!/usr/bin/env bash
# Stage Camp Desk JSON into the model-service Railway build context.
# railway up uses --path-as-root on services/model-service, so repo-root
# content/writers is outside the upload unless we copy it in.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${ROOT}/content/writers/camp-desk-2026"
DST="${ROOT}/services/model-service/content/writers/camp-desk-2026"
if [[ ! -d "$SRC" ]]; then
  echo "missing camp desk: $SRC" >&2
  exit 1
fi
mkdir -p "$(dirname "$DST")"
rm -rf "$DST"
cp -a "$SRC" "$DST"
echo "staged camp desk -> $DST ($(find "$DST" -type f | wc -l) files)"
