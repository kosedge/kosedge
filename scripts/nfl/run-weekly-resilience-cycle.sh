#!/usr/bin/env bash
# Tuesday enterprise resilience cycle:
#   1) resolve active season/week
#   2) launch-hardening ingest (owned tables + snaps/depth)
#   3) in-season weekly update (features → baselines → props)
#   4) DR pg_dump backup + verify
#   5) freshness SLO snapshot
#
# Usage:
#   ./scripts/nfl/run-weekly-resilience-cycle.sh
#   SEASON=2025 WEEK=18 ./scripts/nfl/run-weekly-resilience-cycle.sh
#   SKIP_PLAYER_UPDATE=1 ./scripts/nfl/run-weekly-resilience-cycle.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python3}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}"
export PYTHONPATH="${ROOT_DIR}/services/data-platform-nfl/src${PYTHONPATH:+:$PYTHONPATH}"
export NFL_PG_BIN_DIR="${NFL_PG_BIN_DIR:-/usr/local/opt/postgresql@16/bin}"
MODEL_SERVICE_URL="${MODEL_SERVICE_URL:-http://127.0.0.1:8000}"
SKIP_PLAYER_UPDATE="${SKIP_PLAYER_UPDATE:-0}"
SKIP_DR_BACKUP="${SKIP_DR_BACKUP:-0}"
DRY_RUN="${DRY_RUN:-0}"

resolve_week() {
  "${PYTHON_BIN}" - <<'PY'
import json
import os
from data_platform_nfl.db import SessionLocal
from data_platform_nfl.freshness import resolve_active_season_week
session = SessionLocal()
try:
    season, week = resolve_active_season_week(session)
    print(json.dumps({"season": season, "week": week}))
finally:
    session.close()
PY
}

RESOLVED="$(resolve_week)"
SEASON="${SEASON:-$(echo "$RESOLVED" | "${PYTHON_BIN}" -c 'import sys,json; print(json.load(sys.stdin)["season"] or "")')}"
WEEK="${WEEK:-$(echo "$RESOLVED" | "${PYTHON_BIN}" -c 'import sys,json; print(json.load(sys.stdin)["week"] or "")')}"

if [[ -z "${SEASON}" || -z "${WEEK}" ]]; then
  echo "Unable to resolve SEASON/WEEK from schedules; set them explicitly." >&2
  exit 2
fi

echo "== NFL weekly resilience cycle season=${SEASON} week=${WEEK} =="

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "DRY RUN only — would run launch-hardening, weekly update, DR backup, freshness."
  exit 0
fi

cd "${ROOT_DIR}/services/data-platform-nfl"
echo "== launch-hardening ingest =="
"${PYTHON_BIN}" -m data_platform_nfl.cli \
  --seasons "${SEASON}" \
  --week "${WEEK}" \
  --run-launch-hardening \
  --backup-include-row-exports \
  --backup-export-dir "${ROOT_DIR}/data/ops"

if [[ "${SKIP_PLAYER_UPDATE}" != "1" ]]; then
  echo "== in-season weekly update =="
  SEASON="${SEASON}" WEEK="${WEEK}" MODEL_SERVICE_URL="${MODEL_SERVICE_URL}" \
    bash "${ROOT_DIR}/scripts/nfl/run-weekly-inseason-update.sh"
fi

if [[ "${SKIP_DR_BACKUP}" != "1" ]]; then
  echo "== DR backup =="
  bash "${ROOT_DIR}/scripts/nfl/run-ownership-dr-backup.sh"
fi

echo "== freshness SLO snapshot =="
"${PYTHON_BIN}" -m data_platform_nfl.cli \
  --seasons "${SEASON}" \
  --week "${WEEK}" \
  --evaluate-data-freshness

echo "== resilience cycle complete =="
