#!/usr/bin/env bash
# Finish 100k launch-current publish + K/DST artifact after run_launch_research_sims.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${PY:-/Users/ryankos/kosedge/.venv/bin/python}"
export PYTHONUNBUFFERED=1
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}"

SOURCE="${1:-}"
if [[ -z "$SOURCE" ]]; then
  SOURCE="$(ls -dt data/ops/nfl-season-engine-launch-*Nteam100000-Nplayer1000-* 2>/dev/null | head -1 || true)"
fi
if [[ -z "$SOURCE" || ! -d "$SOURCE" ]]; then
  echo "missing research source dir" >&2
  exit 1
fi
echo "SOURCE=$SOURCE"

"$PY" -u scripts/nfl/publish_nfl_kdst_artifact.py --season 2026 --source "$SOURCE"

set +e
"$PY" -u scripts/nfl/publish_launch_research_to_web.py \
  --source "$SOURCE" \
  --apply-feature-floors \
  --lock-tag nfl-season-engine-2026-preseason-lock
PUB_RC=$?
set -e
if [[ "$PUB_RC" -ne 0 ]]; then
  echo "lock-tag publish failed (rc=$PUB_RC); retrying without lock-tag / release gate"
  "$PY" -u scripts/nfl/publish_launch_research_to_web.py \
    --source "$SOURCE" \
    --apply-feature-floors
fi

echo "DONE source=$SOURCE"
