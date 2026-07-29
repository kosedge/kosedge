#!/usr/bin/env bash
# Full in-season weekly update: rolling usage → features → baselines →
# box scores → props → fantasy/awards. Idempotent; safe to re-run.
#
# Usage:
#   SEASON=2026 WEEK=5 ./scripts/nfl/run-weekly-inseason-update.sh
#   SEASON=2026 WEEK=5 ./scripts/nfl/run-weekly-inseason-update.sh --dry-run
#   SEASON=2026 WEEK=5 SKIP_INGEST=1 ./scripts/nfl/run-weekly-inseason-update.sh
#
# Prerequisite: week W real usage should already be ingestible (nflverse /
# launch-hardening). Pass SKIP_INGEST=1 when owned tables for that week are
# already fresh.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEASON="${SEASON:-2026}"
WEEK="${WEEK:-}"
MODEL_SERVICE_URL="${MODEL_SERVICE_URL:-http://127.0.0.1:8000}"
PLAYER_MODEL_VERSION="${PLAYER_MODEL_VERSION:-nfl-player-v1}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python3}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}"
SKIP_INGEST="${SKIP_INGEST:-0}"
SKIP_FANTASY="${SKIP_FANTASY:-0}"
SKIP_AWARDS="${SKIP_AWARDS:-0}"
TARGET_WEEK_FEATURES_ONLY="${TARGET_WEEK_FEATURES_ONLY:-0}"
# Soft-fail model POSTs by default (local/dev). Set STRICT=1 for prod desks.
STRICT="${STRICT:-0}"
DRY_RUN=0

for arg in "$@"; do
  case "${arg}" in
    --dry-run|-n) DRY_RUN=1 ;;
    --help|-h)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      echo "Usage: SEASON=2026 WEEK=N $0 [--dry-run]" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${WEEK}" ]]; then
  echo "WEEK is required (finished real week to fold into future priors)." >&2
  echo "Example: SEASON=2026 WEEK=5 $0" >&2
  exit 2
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

log() { echo "[inseason-weekly] $*"; }

post_ops() {
  local path="$1"
  local label="$2"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "DRY-RUN skip POST ${MODEL_SERVICE_URL}${path}"
    echo "{\"id\":\"${label}\",\"status\":\"dry_run\",\"path\":\"${path}\"}"
    return 0
  fi
  log "POST ${path}"
  local body
  if ! body="$(curl --fail --silent --show-error --request POST "${MODEL_SERVICE_URL}${path}")"; then
    echo "{\"id\":\"${label}\",\"status\":\"failed\",\"path\":\"${path}\"}"
    return 1
  fi
  echo "{\"id\":\"${label}\",\"status\":\"enqueued\",\"path\":\"${path}\",\"response\":${body}}"
}

run_python_task() {
  local label="$1"
  local expr="$2"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "DRY-RUN skip python task ${label}"
    echo "{\"id\":\"${label}\",\"status\":\"dry_run\"}"
    return 0
  fi
  log "Running ${label}"
  (
    cd "${ROOT_DIR}/services/model-service"
    DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge}" \
      PYTHONPATH=./src "${PYTHON_BIN}" -c "${expr}"
  )
}

log "season=${SEASON} week=${WEEK} dry_run=${DRY_RUN} skip_ingest=${SKIP_INGEST}"

# --- Data platform portion (CLI) ---
DP_FLAGS=(
  --seasons "${SEASON}"
  --week "${WEEK}"
  --run-inseason-weekly-update
)
if [[ "${SKIP_INGEST}" == "1" ]]; then
  DP_FLAGS+=(--skip-ingest)
fi
if [[ "${TARGET_WEEK_FEATURES_ONLY}" == "1" ]]; then
  DP_FLAGS+=(--target-week-features-only)
fi
if [[ "${DRY_RUN}" -eq 1 ]]; then
  DP_FLAGS+=(--dry-run)
fi

log "Data-platform in-season weekly update"
(
  cd "${ROOT_DIR}/services/data-platform-nfl"
  PYTHONPATH=./src "${PYTHON_BIN}" -m data_platform_nfl.cli "${DP_FLAGS[@]}"
)

# --- Model-service rematerialization ---
BASELINES_PATH="/nfl/ops/materialize-player-baselines?season=${SEASON}&week=${WEEK}&model_version=${PLAYER_MODEL_VERSION}"
PROPS_PATH="/nfl/ops/materialize-player-props?season=${SEASON}&week=${WEEK}&model_version=${PLAYER_MODEL_VERSION}"
FANTASY_PATH="/nfl/ops/materialize-fantasy?season=${SEASON}&week=${WEEK}&model_version=${PLAYER_MODEL_VERSION}"
AWARDS_PATH="/nfl/ops/materialize-award-projections?season=${SEASON}&model_version=${PLAYER_MODEL_VERSION}&top_n=10"

soft_or_strict() {
  if [[ "${STRICT}" == "1" ]]; then
    "$@"
  else
    "$@" || true
  fi
}

soft_or_strict post_ops "${BASELINES_PATH}" "materialize_player_baselines"

soft_or_strict run_python_task "materialize_box_score_sims" \
  "from src.tasks import materialize_nfl_player_box_score_sims as m; import json; print(json.dumps(m(season=${SEASON}, week=${WEEK}), default=str))"

soft_or_strict post_ops "${PROPS_PATH}" "materialize_prop_edges"

if [[ "${SKIP_FANTASY}" != "1" ]]; then
  soft_or_strict post_ops "${FANTASY_PATH}" "materialize_fantasy_weekly"
else
  log "Skipping fantasy weekly (SKIP_FANTASY=1)"
fi

if [[ "${SKIP_AWARDS}" != "1" ]]; then
  soft_or_strict post_ops "${AWARDS_PATH}" "materialize_award_projections"
else
  log "Skipping awards (SKIP_AWARDS=1)"
fi

# --- Projections Hub Actual column (team W/L + player season-to-date) ---
log "Writing Projections Hub actuals JSON"
if [[ "${DRY_RUN}" -eq 1 ]]; then
  log "DRY-RUN skip write_projection_actuals.py"
else
  (
    cd "${ROOT_DIR}"
    DATABASE_URL="${DATABASE_URL}" \
      "${PYTHON_BIN}" scripts/nfl/write_projection_actuals.py --season "${SEASON}" --from-db \
      || log "WARN: projection actuals writer failed (hub can still use live /nfl/ops/projection-actuals)"
  )
fi

log "Done. Re-run safely any time; DP steps upsert/replace, model ops enqueue/idempotent rematerialize."
log "STRICT=${STRICT} (set STRICT=1 to fail the script on model-step errors)."
log "Desk: /pro/nfl/fair-lines → /pro/nfl/edges → /pro/nfl/props → /pro/nfl/projections"
