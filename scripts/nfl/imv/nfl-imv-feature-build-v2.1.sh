#!/usr/bin/env bash
# nfl-imv-feature-build-v2.1.sh
# fd97f103 C-3. File-backed nflverse feature store. NOT the sealed run.
#
# DO NOT RUN until IMV code-checks this builder. W7 refused.
# Network OFF. Never DATABASE_URL / Odds / Railway. Never ~/kosedge.
#
# Usage (after IMV code-check):
#   bash nfl-imv-feature-build-v2.1.sh \
#     --base /abs/dedicated-b1d857d3-worktree \
#     --prestage /var/tmp/nfl-imv-prestage-nflverse/LATEST \
#     --out /var/tmp/nfl-imv-features/<UTC> \
#     --game-week-cap 6 --pbp-week-cap 5
#
# Week caps are required. Retro W4–W6: game-week-cap=6, pbp-week-cap=5
# (W6 games use PBP through W5). W8: game-week-cap=8, pbp-week-cap=7.
# Rolling window is PRIOR weeks only (AND 1 PRECEDING), not prod CURRENT ROW.

set -euo pipefail

SCRIPT_ID="nfl-imv-feature-build-v2.1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="${SCRIPT_DIR}/nfl_imv_v21.py"
CERT_CANDIDATE="b1d857d356d5afc422c86ffb1e9a25afdf2a4225"

export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0

BASE=""
PRESTAGE=""
OUT=""
GAME_WEEK_CAP=""
PBP_WEEK_CAP=""
PACK=""

usage() {
  printf '%s\n' "Usage: bash $0 --base BASE --prestage DIR --out DIR --game-week-cap N --pbp-week-cap N" >&2
  printf '%s\n' "DO NOT RUN until IMV code-checks. W7 refused. Caps required." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="${2:-}"; shift 2 ;;
    --prestage) PRESTAGE="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --game-week-cap) GAME_WEEK_CAP="${2:-}"; shift 2 ;;
    --pbp-week-cap) PBP_WEEK_CAP="${2:-}"; shift 2 ;;
    --pack) PACK="${2:-}"; shift 2 ;;
    w7|w7-pregame)
      printf '%s\n' "FAIL: W7 mode refused (fd97f103)." >&2
      exit 2 ;;
    -h|--help) usage; exit 2 ;;
    *) printf '%s\n' "FAIL: unknown arg $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${BASE}" || -z "${PRESTAGE}" || -z "${OUT}" || -z "${GAME_WEEK_CAP}" || -z "${PBP_WEEK_CAP}" ]]; then
  usage
  exit 2
fi

if [[ ! -f "${HELPER}" ]]; then
  printf '%s\n' "FAIL: missing ${HELPER}" >&2
  exit 2
fi

if [[ "${BASE}" != /* || "${OUT}" != /* ]]; then
  printf '%s\n' "FAIL: --base and --out must be absolute" >&2
  exit 2
fi

if [[ "${BASE}" == "${HOME}/kosedge" || "${BASE}" == "${HOME}/kosedge/" ]]; then
  printf '%s\n' "FAIL: S-1 BASE must not be ~/kosedge" >&2
  exit 2
fi

REPO="$(git -C "${BASE}" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${REPO}" ]]; then
  printf '%s\n' "FAIL: --base is not a git worktree" >&2
  exit 2
fi
HEAD="$(git -C "${REPO}" rev-parse HEAD)"
if [[ "${HEAD}" != "${CERT_CANDIDATE}" ]]; then
  printf '%s\n' "FAIL: BASE HEAD ${HEAD} != ${CERT_CANDIDATE}" >&2
  exit 2
fi
if [[ -n "$(git -C "${REPO}" status --porcelain)" ]]; then
  printf '%s\n' "FAIL: BASE is dirty" >&2
  exit 2
fi

for ev in DATABASE_URL ODDS_API_KEY THE_ODDS_API_KEY MODEL_SERVICE_URL RAILWAY_TOKEN; do
  if [[ -n "${!ev:-}" ]]; then
    printf '%s\n' "FAIL: env ${ev} is set (value not printed)" >&2
    exit 2
  fi
done

if [[ -d "${PRESTAGE}" ]]; then
  PRESTAGE_DIR="${PRESTAGE}"
elif [[ -f "${PRESTAGE}" ]]; then
  PRESTAGE_DIR="$(tr -d '\n' < "${PRESTAGE}")"
else
  printf '%s\n' "FAIL: --prestage is not a dir or LATEST pointer" >&2
  exit 2
fi

MANIFEST="${PRESTAGE_DIR}/imv-manifest.tsv"
if [[ ! -f "${MANIFEST}" ]]; then
  MANIFEST="${PRESTAGE_DIR}/imv-w7-manifest.tsv"
fi
if [[ ! -f "${MANIFEST}" ]]; then
  printf '%s\n' "FAIL: no imv-manifest.tsv in ${PRESTAGE_DIR}" >&2
  exit 2
fi

GAMES=""
PBP_ARGS=()
while IFS=$'\t' read -r sha path role as_of; do
  [[ -z "${sha}" || "${sha}" == \#* ]] && continue
  fp="${path}"
  if [[ "${fp}" != /* ]]; then
    fp="${PRESTAGE_DIR}/${path}"
  fi
  if [[ ! -f "${fp}" ]]; then
    printf '%s\n' "FAIL: missing ${fp}" >&2
    exit 2
  fi
  got="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${fp}")"
  if [[ "${got}" != "${sha}" ]]; then
    printf '%s\n' "FAIL: sha mismatch ${fp}" >&2
    exit 2
  fi
  case "${role}" in
    schedule_games_csv) GAMES="${fp}" ;;
    pbp_2025|pbp_2026) PBP_ARGS+=(--pbp "${fp}") ;;
  esac
done < "${MANIFEST}"

if [[ -z "${GAMES}" || ${#PBP_ARGS[@]} -lt 1 ]]; then
  printf '%s\n' "FAIL: manifest needs schedule_games_csv + pbp_2025/pbp_2026" >&2
  exit 2
fi

mkdir -p "${OUT}"
PACK_ARG=()
if [[ -n "${PACK}" ]]; then
  PACK_ARG=(--pack "${PACK}")
fi

# Builder body — IMV must code-check before this is executed on a live prestage.
python3 "${HELPER}" build \
  --base "${REPO}" \
  --games-csv "${GAMES}" \
  "${PBP_ARGS[@]}" \
  --out "${OUT}" \
  --game-week-cap "${GAME_WEEK_CAP}" \
  --pbp-week-cap "${PBP_WEEK_CAP}" \
  "${PACK_ARG[@]}"

if [[ -d /var/tmp/nfl-imv-features ]]; then
  ln -sfn "${OUT}" /var/tmp/nfl-imv-features/LATEST
fi

printf '%s\n' "${SCRIPT_ID} wrote ${OUT} FEATURE_STORE.sha256=$(tr -d '\n' < "${OUT}/FEATURE_STORE.sha256")"
