#!/usr/bin/env bash
# DR backup entrypoint for model-service containers (and local monorepo).
# Prefer vendored data_platform_nfl on PYTHONPATH=/app in Railway images.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# .../scripts/nfl -> app or repo root candidates
APP_OR_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -d "${APP_OR_ROOT}/data_platform_nfl" ]]; then
  ROOT_DIR="${APP_OR_ROOT}"
  export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:$PYTHONPATH}"
elif [[ -d "${APP_OR_ROOT}/services/data-platform-nfl/src/data_platform_nfl" ]]; then
  ROOT_DIR="$(cd "${APP_OR_ROOT}" && pwd)"
  export PYTHONPATH="${ROOT_DIR}/services/data-platform-nfl/src${PYTHONPATH:+:$PYTHONPATH}"
else
  # Fallback: monorepo layout when script lives at repo/scripts/nfl
  ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  export PYTHONPATH="${ROOT_DIR}/services/data-platform-nfl/src${PYTHONPATH:+:$PYTHONPATH}"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}"
export NFL_DR_BACKUP_DIR="${NFL_DR_BACKUP_DIR:-${ROOT_DIR}/data/backups/nfl}"
# Prefer system pg tools in containers; Homebrew path is local-dev only.
export NFL_PG_BIN_DIR="${NFL_PG_BIN_DIR:-/usr/bin}"

VERIFY_FLAG=()
UPLOAD_FLAG=()
if [[ "${SKIP_VERIFY:-0}" == "1" ]]; then
  VERIFY_FLAG=(--skip-dr-verify)
fi
if [[ "${SKIP_UPLOAD:-0}" == "1" ]]; then
  UPLOAD_FLAG=(--skip-dr-upload)
fi

mkdir -p "${NFL_DR_BACKUP_DIR}"
cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" -m data_platform_nfl.cli --run-dr-backup ${VERIFY_FLAG[@]+"${VERIFY_FLAG[@]}"} ${UPLOAD_FLAG[@]+"${UPLOAD_FLAG[@]}"}
