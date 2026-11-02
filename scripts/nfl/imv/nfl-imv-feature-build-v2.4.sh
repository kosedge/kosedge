#!/usr/bin/env bash
# nfl-imv-feature-build-v2.4.sh
# 47616a70 C-1..C-6. NOT the sealed run. Frozen helpers: v22=57a419b4 v23=fe66b374.
#
# IMV dir is THIS script's folder, which must sit OUTSIDE --base (never
# $BASE/scripts). Bundle copies v21/v22/v23/v24 + feature-path + README.
# C-5 BLOCK on helper pin mismatch. C-6 store SHA256SUMS written last.
# Darwin + sandbox-exec network deny + EPERM probe (X-8).
# Refuses an existing --out directory (X-9). W7 refused.
#
# Caps (X-5): --game-week-cap 6 --pbp-week-cap 5   (W4–W6 RETROSPECTIVE)
#             --game-week-cap 8 --pbp-week-cap 7   (W8 PROSPECTIVE-RESEARCH)
# pbp MUST equal game-1. W7 mode refused.

set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0

SCRIPT_ID="nfl-imv-feature-build-v2.4"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="${SCRIPT_DIR}/$(basename "$0")"
HELPER="${SCRIPT_DIR}/nfl_imv_v22.py"
HELPER_V21="${SCRIPT_DIR}/nfl_imv_v21.py"
HELPER_V23="${SCRIPT_DIR}/nfl_imv_v23.py"
HELPER_V24="${SCRIPT_DIR}/nfl_imv_v24.py"
CERT_CANDIDATE="b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
V21_PIN="050271467cd38f5a174043c67f2df9622d7f0b8125f137b822f888846f4c561f"
V22_PIN="57a419b42f743dafb590d3dff8b40b7f89769db04d38ce2f48453bc0f85b1843"
V23_PIN="fe66b374905817b1e991bc7260554dc8c706d8a487baf4876bc04bc1436d0470"

BASE=""
PRESTAGE=""
OUT=""
GAME_WEEK_CAP=""
PBP_WEEK_CAP=""
PACK=""

usage() {
  printf '%s\n' "Usage: bash $0 --base BASE --prestage DIR --out DIR --game-week-cap {4|5|6|8} --pbp-week-cap N" >&2
  printf '%s\n' "X-5: pbp-week-cap must be game-week-cap-1. W7 refused. X-9: --out must not exist." >&2
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
      printf '%s\n' "FAIL: W7 mode refused (47616a70)." >&2
      exit 2 ;;
    -h|--help) usage; exit 2 ;;
    *) printf '%s\n' "FAIL: unknown arg $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${BASE}" || -z "${PRESTAGE}" || -z "${OUT}" || -z "${GAME_WEEK_CAP}" || -z "${PBP_WEEK_CAP}" ]]; then
  usage
  exit 2
fi
if [[ "${GAME_WEEK_CAP}" == "7" ]]; then
  printf '%s\n' "FAIL: W7 refused (X-5)." >&2
  exit 2
fi
if [[ "${PBP_WEEK_CAP}" != "$((GAME_WEEK_CAP - 1))" ]]; then
  printf '%s\n' "FAIL: X-5 cap pair pbp=${PBP_WEEK_CAP} != game-1 ($((GAME_WEEK_CAP - 1)))" >&2
  exit 2
fi
if [[ ! -f "${HELPER}" || ! -f "${HELPER_V21}" || ! -f "${HELPER_V23}" || ! -f "${HELPER_V24}" ]]; then
  printf '%s\n' "FAIL: missing helper (need nfl_imv_v21.py + v22 + v23 + v24)" >&2
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
# X-9: refuse existing output dir (do not mkdir -p over it).
if [[ -e "${OUT}" ]]; then
  printf '%s\n' "FAIL: X-9 --out already exists: ${OUT}" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  printf '%s\n' "FAIL: ${SCRIPT_ID} must run on Ryan's Mac (Darwin). Host=$(uname -s)." >&2
  exit 2
fi

if [[ -z "${IMV_BUILD_SANDBOXED:-}" ]]; then
  command -v sandbox-exec >/dev/null 2>&1 || { printf '%s\n' "FAIL: sandbox-exec missing" >&2; exit 2; }
  export IMV_BUILD_SANDBOXED=1
  exec sandbox-exec -p '(version 1)
(allow default)
(deny network*)
(deny network-outbound)
(deny network-inbound)
' /bin/bash "$SCRIPT_PATH" --base "${BASE}" --prestage "${PRESTAGE}" --out "${OUT}" \
    --game-week-cap "${GAME_WEEK_CAP}" --pbp-week-cap "${PBP_WEEK_CAP}" ${PACK:+--pack "${PACK}"}
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
# Returned (1): IMV scripts must not live inside BASE.
IMV_GATE="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import nfl_imv_v24 as v; import json; print(json.dumps(v.refuse_imv_inside_base(sys.argv[1], sys.argv[2])))' "${SCRIPT_DIR}" "${REPO}")"
if [[ "${IMV_GATE}" != *'"ok": true'* && "${IMV_GATE}" != *'"ok":true'* ]]; then
  printf '%s\n' "FAIL: IMV dir is inside BASE. Use a sha-checked folder outside BASE. ${IMV_GATE}" >&2
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

mkdir "${OUT}"
export FIXED_OUT="${OUT}"
date -u +%Y-%m-%dT%H:%M:%SZ > "${OUT}/BUILD_STARTED_UTC"
export IMV_BUILD_STARTED_UTC="$(tr -d '\n' < "${OUT}/BUILD_STARTED_UTC")"
# X-8: EPERM probe inside OUT
python3 - <<'PY'
import errno, json, os, socket, sys
out = os.environ["FIXED_OUT"]
doc = {"probe": "connect 1.1.1.1:443", "result": None, "errno": None}
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2.0)
try:
    s.connect(("1.1.1.1", 443))
except OSError as e:
    doc["errno"] = e.errno
    if e.errno == errno.EPERM:
        doc["result"] = "EPERM_OK"
        open(os.path.join(out, "EPERM_PROBE.json"), "w").write(json.dumps(doc, indent=2) + "\n")
        open(os.path.join(out, "EPERM_PROBE.txt"), "w").write("EPERM_OK\n")
        sys.exit(0)
    doc["result"] = "NETWORK_DENY_NOT_EPERM"
    open(os.path.join(out, "EPERM_PROBE.json"), "w").write(json.dumps(doc, indent=2) + "\n")
    sys.exit(3)
else:
    s.close()
    doc["result"] = "NETWORK_REACHABLE"
    open(os.path.join(out, "EPERM_PROBE.json"), "w").write(json.dumps(doc, indent=2) + "\n")
    sys.exit(3)
PY
EPERM_RC=$?
if [[ "${EPERM_RC}" -ne 0 ]]; then
  printf '%s\n' "FAIL: X-8 EPERM probe rc=${EPERM_RC}" >&2
  exit 3
fi

HELPER_SHA="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${HELPER}")"
HELPER_V21_SHA="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${HELPER_V21}")"
HELPER_V23_SHA="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${HELPER_V23}")"
if [[ "${HELPER_V21_SHA}" != "${V21_PIN}" ]]; then
  printf '%s\n' "FAIL: C-5 nfl_imv_v21.py sha ${HELPER_V21_SHA} != ${V21_PIN}" >&2
  exit 2
fi
if [[ "${HELPER_SHA}" != "${V22_PIN}" ]]; then
  printf '%s\n' "FAIL: C-5 nfl_imv_v22.py sha ${HELPER_SHA} != ${V22_PIN} (57a419b4)" >&2
  exit 2
fi
if [[ "${HELPER_V23_SHA}" != "${V23_PIN}" ]]; then
  printf '%s\n' "FAIL: C-5 nfl_imv_v23.py sha ${HELPER_V23_SHA} != ${V23_PIN} (fe66b374)" >&2
  exit 2
fi
python3 "${HELPER_V24}" stamp-helpers --imv-dir "${SCRIPT_DIR}" --out "${OUT}"
if [[ $? -ne 0 ]]; then
  printf '%s\n' "FAIL: C-5 helper pin BLOCK" >&2
  exit 2
fi
python3 "${HELPER_V24}" write-bundle --imv-dir "${SCRIPT_DIR}" --out "${OUT}/bundle"
printf '%s\n' "${HELPER_SHA}" > "${OUT}/HELPER.sha256"
printf '%s\n' "${HELPER_V21_SHA}" > "${OUT}/HELPER_V21.sha256"
printf '%s\n' "${HELPER_SHA}" > "${OUT}/HELPER_V22.sha256"
printf '%s\n' "${HELPER_V23_SHA}" > "${OUT}/HELPER_V23.sha256"

PACK_ARG=()
if [[ -n "${PACK}" ]]; then
  PACK_ARG=(--pack "${PACK}")
fi

# build_feature_store refuses if out_dir exists — pin EPERM/HELPER into a sibling
# and pass a fresh FEATURE_DIR? X-9 is --out. We already created OUT for probes.
# Python build is told to write into OUT/store so OUT itself is the stamp dir
# already created. Override: write features into OUT (exists). The Python
# exists() check would BLOCK. So we pass --out "${OUT}/store" which must not exist.
FEATURE_DIR="${OUT}/store"
set +e
python3 "${HELPER}" build \
  --base "${REPO}" \
  --games-csv "${GAMES}" \
  "${PBP_ARGS[@]}" \
  --out "${FEATURE_DIR}" \
  --game-week-cap "${GAME_WEEK_CAP}" \
  --pbp-week-cap "${PBP_WEEK_CAP}" \
  "${PACK_ARG[@]}"
BUILD_RC=$?
set -e

python3 "${HELPER_V24}" stamp-helpers --imv-dir "${SCRIPT_DIR}" --out "${FEATURE_DIR}"
printf '%s\n' "${HELPER_V21_SHA}" > "${OUT}/HELPER_V21.sha256"
printf '%s\n' "${HELPER_SHA}" > "${OUT}/HELPER_V22.sha256"
printf '%s\n' "${HELPER_V23_SHA}" > "${OUT}/HELPER_V23.sha256"
printf '%s\n' "${HELPER_SHA}" > "${OUT}/HELPER.sha256"
# C-6: SHA256SUMS last in the store (after helper stamps / build-report).
python3 "${HELPER_V24}" write-store-sums --store "${FEATURE_DIR}"

if [[ -f "${FEATURE_DIR}/build-report.json" ]]; then
  BUILD_STATUS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "${FEATURE_DIR}/build-report.json")"
  if [[ "${BUILD_STATUS}" == "BLOCKED" ]]; then
    printf '%s\n' "BLOCKED" > "${OUT}/BUILD_BLOCKED"
    printf '%s\n' "FAIL: P-5 BLOCKED build — do not start a sealed run. Re-run is a new --out." >&2
    exit 6
  fi
fi
if [[ "${BUILD_RC}" -ne 0 ]]; then
  printf '%s\n' "BLOCKED" > "${OUT}/BUILD_BLOCKED"
  printf '%s\n' "FAIL: P-5 builder rc=${BUILD_RC} — do not start a sealed run." >&2
  exit "${BUILD_RC}"
fi
printf '%s\n' "${SCRIPT_ID} helper_v21=${HELPER_V21_SHA} helper_v22=${HELPER_SHA} helper_v23=${HELPER_V23_SHA} store=${FEATURE_DIR}"
printf '%s\n' "PIN_THIS_SHA_OUTSIDE=$(tr -d '\n' < "${FEATURE_DIR}/FEATURE_STORE.sha256" 2>/dev/null || true)"
printf '%s\n' "DELIVER_STORE_SHA_TO_BOX_BEFORE_SEAL=1"
