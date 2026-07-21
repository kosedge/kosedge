#!/usr/bin/env bash
# Enterprise NFL warehouse DR backup: compressed pg_dump + verify + retention.
#
# Usage:
#   ./scripts/nfl/run-ownership-dr-backup.sh
#   SKIP_VERIFY=1 ./scripts/nfl/run-ownership-dr-backup.sh
#   NFL_DR_REMOTE_URI=s3://bucket/path ./scripts/nfl/run-ownership-dr-backup.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python3}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}"
export PYTHONPATH="${ROOT_DIR}/services/data-platform-nfl/src${PYTHONPATH:+:$PYTHONPATH}"
export NFL_PG_BIN_DIR="${NFL_PG_BIN_DIR:-/usr/local/opt/postgresql@16/bin}"
export NFL_DR_BACKUP_DIR="${NFL_DR_BACKUP_DIR:-${ROOT_DIR}/data/backups/nfl}"

VERIFY_FLAG=()
UPLOAD_FLAG=()
if [[ "${SKIP_VERIFY:-0}" == "1" ]]; then
  VERIFY_FLAG=(--skip-dr-verify)
fi
if [[ "${SKIP_UPLOAD:-0}" == "1" ]]; then
  UPLOAD_FLAG=(--skip-dr-upload)
fi

cd "${ROOT_DIR}/services/data-platform-nfl"
"${PYTHON_BIN}" -m data_platform_nfl.cli --run-dr-backup ${VERIFY_FLAG[@]+"${VERIFY_FLAG[@]}"} ${UPLOAD_FLAG[@]+"${UPLOAD_FLAG[@]}"}
