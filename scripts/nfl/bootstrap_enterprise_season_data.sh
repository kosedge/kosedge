#!/usr/bin/env bash
# Bootstrap / refresh owned NFL data products needed for a full season of
# enterprise sharpening (snaps, depth, tendencies, features).
#
# Usage:
#   SEASONS=2024,2025,2026 ./scripts/nfl/bootstrap_enterprise_season_data.sh
#   SEASONS=2025,2026 SKIP_PBP=1 ./scripts/nfl/bootstrap_enterprise_season_data.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python3}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}"
SEASONS_CSV="${SEASONS:-2024,2025,2026}"
SKIP_PBP="${SKIP_PBP:-0}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

log() { echo "[enterprise-bootstrap] $*"; }

IFS=',' read -r -a SEASON_ARR <<< "${SEASONS_CSV}"
log "seasons=${SEASONS_CSV} skip_pbp=${SKIP_PBP}"

cd "${ROOT_DIR}/services/data-platform-nfl"
export PYTHONPATH=./src

for season in "${SEASON_ARR[@]}"; do
  season="$(echo "${season}" | tr -d '[:space:]')"
  [[ -z "${season}" ]] && continue
  log "=== season ${season} ==="
  if [[ "${SKIP_PBP}" != "1" ]]; then
    log "launch hardening (includes PBP/usage/injuries where available)"
    "${PYTHON_BIN}" -m data_platform_nfl.cli --seasons "${season}" --run-launch-hardening || true
  fi
  log "snap counts (GSIS bridge)"
  "${PYTHON_BIN}" -m data_platform_nfl.cli --seasons "${season}" --ingest-snap-counts
  log "official depth charts"
  "${PYTHON_BIN}" -m data_platform_nfl.cli --seasons "${season}" --ingest-official-depth-charts || true
  log "tendency profiles"
  "${PYTHON_BIN}" -m data_platform_nfl.cli --seasons "${season}" --materialize-tendency-profiles || true
  log "player projection features"
  "${PYTHON_BIN}" -m data_platform_nfl.cli --seasons "${season}" \
    --materialize-player-projection-features --replace-player-projection-features || true
done

log "Done. Next: SEASON=2026 WEEK=<N> ./scripts/nfl/run-weekly-inseason-update.sh"
