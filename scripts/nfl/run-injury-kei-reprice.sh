#!/usr/bin/env bash
# NFL Kickoff Injury → KEI cadence (ET windows).
#
# Usage:
#   ./scripts/nfl/run-injury-kei-reprice.sh --window friday_final --dry-run
#   ./scripts/nfl/run-injury-kei-reprice.sh --window midweek --fixture --dry-run
#   WEEK=1 ./scripts/nfl/run-injury-kei-reprice.sh --window gameday_inactives --fixture --dry-run
#   ./scripts/nfl/run-injury-kei-reprice.sh --explain-friday
#
# Config: data/ops/nfl-injury-kei-cadence/config.json
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEASON="${SEASON:-2026}"
WEEK="${WEEK:-1}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python3}"
EXTRA_ARGS=()

usage() {
  sed -n '2,12p' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window)
      EXTRA_ARGS+=(--window "$2")
      shift 2
      ;;
    --dry-run|-n)
      EXTRA_ARGS+=(--dry-run)
      shift
      ;;
    --fixture)
      EXTRA_ARGS+=(--fixture)
      shift
      ;;
    --explain-friday)
      EXTRA_ARGS+=(--explain-friday)
      shift
      ;;
    --sot-before|--sot-after|--games)
      EXTRA_ARGS+=("$1" "$2")
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" scripts/nfl/injury_kei_reprice.py \
  --season "${SEASON}" \
  --week "${WEEK}" \
  "${EXTRA_ARGS[@]}"
