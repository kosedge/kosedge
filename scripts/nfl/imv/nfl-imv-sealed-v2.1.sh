#!/usr/bin/env bash
# nfl-imv-sealed-v2.1.sh
# fd97f103 — v2.1 (v2 PASS WITH CONDITIONS). Do NOT run w7-pregame.
# Do NOT run this seal until IMV code-checks the builder.
# C-1 pin feature-store sha  C-2 per-row as-of (prior weeks, pre-kickoff)
# C-4 no explicit_zero injury  C-5 missing kickoff BLOCKED
# C-6 BLOCKED_NO_MODEL_EXECUTION + W## week parse
# C-7 HFA from pinned code == 1.05
# C-8 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 EPERM inside seal.
#
# Targets:
#   retrospective-w4w6   RETROSPECTIVE numbers (W4–W6)
#   w8-pregame           PROSPECTIVE-RESEARCH, seal before 2026-10-30T00:15:00Z
#
# Usage (Ryan's Mac):
#   bash nfl-imv-sealed-v2.1.sh --base /abs/dedicated-b1d857d3-worktree retrospective-w4w6
#   bash nfl-imv-sealed-v2.1.sh --base /abs/dedicated-b1d857d3-worktree w8-pregame
#   IMV_FEATURE_STORE_SHA=<digest from FEATURE_STORE.sha256>  # C-1 required
#
# S-1: --base is a dedicated worktree. Never ~/kosedge. Runner never checkouts.
#      BASE must be exactly b1d857d3, clean, no patches.
# P-a: BLOCKED still seals (set +e after FIXED_OUT; imv_seal always writes SHA256SUMS).
# P-b: LATEST may be a symlink-dir OR a v1 text pointer. Both resolve.
# Null model_spread_home / model_total / model_home_win_prob => BLOCKED.
#
# Feature store (file-backed; see nfl-imv-feature-path-v2.1.md):
#   IMV_FEATURE_STORE=/var/tmp/nfl-imv-features/LATEST
#   IMV_FEATURE_STORE_SHA=...   (C-1: BLOCK on mismatch / missing pin)
#   IMV_MANIFEST=...   (else resolved from pre-stage LATEST)
#
# Never writes the git worktree. Never Odds / Railway / prod DB.

set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0

SCRIPT_ID="nfl-imv-sealed-v2.1"
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_CANDIDATE="b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
AUDIT_SHA="20d51f220ce772545161ae5ce4ed22041110a150"
MERGE_BASE_PREFIX="4aeab78f"
EXPECT_CANDIDATE_AHEAD_OF_AUDIT="85"
EXPECT_AUDIT_AHEAD_OF_CANDIDATE="12"
PROTOCOL="nfl-spread-validation-protocol-v1.0"
MODEL_VERSION="nfl-v1.5-matchup-sim"
STAMP_FULL_PIPELINE_SIMS="1500"
STAMP_HISTORICAL_SIMS="1200"
STAMP_BOOTSTRAP_SEED="7"
STAMP_BLEND_WEIGHT="0.30"
W8_FIRST_KICKOFF_UTC="2026-10-30T00:15:00Z"
W6_FINALS_SOURCE="nflverse"
APPROVAL="fd97f103"

OUT_RETRO_BASE="/var/tmp/nfl-imv-sealed-v2.1-retrospective-w4w6"
OUT_W8_BASE="/var/tmp/nfl-imv-sealed-v2.1-w8-pregame"
PRESTAGE_LATEST="/var/tmp/nfl-imv-prestage-nflverse/LATEST"
FEATURE_LATEST_DEFAULT="/var/tmp/nfl-imv-features/LATEST"

BASE=""
MODE=""
FIXED_OUT=""
RUN_RC=1
REPO=""

usage() {
  printf '%s\n' "Usage: bash $0 --base /abs/dedicated-b1d857d3-worktree {retrospective-w4w6|w8-pregame}" >&2
  printf '%s\n' "S-1: --base is not ~/kosedge and is never checked out by this runner." >&2
  printf '%s\n' "w7-pregame is refused (e0bdcc1a)." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      BASE="${2:-}"; shift 2 ;;
    --base=*)
      BASE="${1#--base=}"; shift ;;
    -h|--help)
      usage; exit 2 ;;
    retrospective-w4w6|w8-pregame)
      MODE="$1"; shift ;;
    w7-pregame|w7)
      printf '%s\n' "FAIL: w7-pregame is refused (fd97f103). Use retrospective-w4w6 or w8-pregame." >&2
      exit 2 ;;
    *)
      printf '%s\n' "FAIL: unknown arg $1" >&2
      usage; exit 2 ;;
  esac
done

if [[ -z "${BASE}" || -z "${MODE}" ]]; then
  usage; exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  printf '%s\n' "FAIL: ${SCRIPT_ID} must run on Ryan's Mac (Darwin). Host=$(uname -s)." >&2
  exit 2
fi

if [[ -z "${IMV_SEALED_SANDBOXED:-}" ]]; then
  command -v sandbox-exec >/dev/null 2>&1 || { printf '%s\n' "FAIL: sandbox-exec missing" >&2; exit 2; }
  export IMV_SEALED_SANDBOXED=1
  exec sandbox-exec -p '(version 1)
(allow default)
(deny network*)
(deny network-outbound)
(deny network-inbound)
' /bin/bash "$SCRIPT_PATH" --base "${BASE}" "${MODE}"
fi

# Snapshot dir first — C-8 EPERM result must land inside the seal (P-a).
CAP_NOW="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ "${MODE}" == "w8-pregame" ]]; then
  FIXED_OUT="${OUT_W8_BASE}/${CAP_NOW}"
else
  FIXED_OUT="${OUT_RETRO_BASE}/${CAP_NOW}"
fi
if [[ -f "${FIXED_OUT}/SHA256SUMS" ]]; then
  printf '%s\n' "FAIL: ${FIXED_OUT} already sealed. Re-run is a new snapshot." >&2
  exit 2
fi
mkdir -p "${FIXED_OUT}"
export FIXED_OUT
: > "${FIXED_OUT}/console.log"

# P-a: disable -e so BLOCKED / cmp / git noise cannot skip the seal.
set +e

sha256_file() { shasum -a 256 "$1" | awk '{print $1}'; }

say() { printf '%s\n' "$*" | tee -a "${FIXED_OUT}/console.log" >&2; }

imv_seal() {
  # Must never fail-open past SHA256SUMS. Inherit set +e.
  local rc="${1:-1}"
  trap - EXIT
  set +e
  if [[ -d "${FIXED_OUT}" ]]; then
    [[ -f "${FIXED_OUT}/EXIT_CODE" ]] || printf '%s\n' "${rc}" > "${FIXED_OUT}/EXIT_CODE"
    rc="$(cat "${FIXED_OUT}/EXIT_CODE" 2>/dev/null || echo "${rc}")"
    if [[ -d "${REPO:-}" && ! -f "${FIXED_OUT}/git-status-after.txt" ]]; then
      {
        echo "HEAD=$(git -C "${REPO}" rev-parse HEAD 2>/dev/null || echo unknown)"
        git -C "${REPO}" status --porcelain=v2 --untracked-files=all --branch 2>/dev/null
      } > "${FIXED_OUT}/git-status-after.txt"
    fi
    python3 - <<PY
import json, os
from datetime import datetime, timezone
p = os.path.join("${FIXED_OUT}", "execution-stamp.json")
doc = {}
if os.path.isfile(p):
    try:
        doc = json.load(open(p))
    except Exception:
        doc = {}
doc.update({
    "script_id": "${SCRIPT_ID}",
    "mode": "${MODE}",
    "model_version": "${MODEL_VERSION}",
    "code_sha": "${CERT_CANDIDATE}",
    "base": "${BASE}",
    "execution_finished_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
})
open(p, "w").write(json.dumps(doc, indent=2) + "\n")
PY
    if [[ ! -f "${FIXED_OUT}/SHA256SUMS" ]]; then
      (
        cd "${FIXED_OUT}"
        find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | while IFS= read -r f; do
          shasum -a 256 "${f}"
        done
      ) > "${FIXED_OUT}/SHA256SUMS"
    fi
  fi
  exit "${rc}"
}
trap 'imv_seal $?' EXIT

# C-8: EPERM probe after FIXED_OUT exists. Result is sealed even on fail.
python3 - <<PY
import errno, json, os, socket, sys
out = os.environ.get("FIXED_OUT") or "${FIXED_OUT}"
doc = {"probe": "connect 1.1.1.1:443", "result": None, "errno": None, "label": None}
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2.0)
try:
    s.connect(("1.1.1.1", 443))
except OSError as e:
    doc["errno"] = e.errno
    if e.errno == errno.EPERM:
        doc["result"] = "EPERM_OK"
        doc["label"] = "EPERM"
        open(os.path.join(out, "EPERM_PROBE.json"), "w").write(json.dumps(doc, indent=2) + "\\n")
        open(os.path.join(out, "EPERM_PROBE.txt"), "w").write("EPERM_OK\\n")
        sys.stdout.write("EPERM_OK\\n")
        sys.exit(0)
    doc["result"] = "NETWORK_DENY_NOT_EPERM"
    doc["label"] = "NOT_EPERM"
    open(os.path.join(out, "EPERM_PROBE.json"), "w").write(json.dumps(doc, indent=2) + "\\n")
    open(os.path.join(out, "EPERM_PROBE.txt"), "w").write("NETWORK_DENY_NOT_EPERM errno=%s\\n" % e.errno)
    sys.stderr.write("NETWORK_DENY_NOT_EPERM errno=%s\\n" % e.errno)
    sys.exit(3)
else:
    s.close()
    doc["result"] = "NETWORK_REACHABLE"
    doc["label"] = "REACHABLE"
    open(os.path.join(out, "EPERM_PROBE.json"), "w").write(json.dumps(doc, indent=2) + "\\n")
    open(os.path.join(out, "EPERM_PROBE.txt"), "w").write("NETWORK_REACHABLE\\n")
    sys.stderr.write("NETWORK_REACHABLE\\n")
    sys.exit(3)
PY
EPERM_RC=$?
if [[ "${EPERM_RC}" -ne 0 ]]; then
  say "FAIL: C-8 EPERM probe rc=${EPERM_RC} (result sealed in EPERM_PROBE.json)"
  RUN_RC=3
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi

say "${SCRIPT_ID} mode=${MODE} approval=${APPROVAL}"
say "fixed_out ${FIXED_OUT}"
say "base ${BASE}"

for ev in DATABASE_URL ODDS_API_KEY THE_ODDS_API_KEY ODDS_API_KEY_NFL MODEL_SERVICE_URL RAILWAY_TOKEN INTERNAL_API_SECRET; do
  if [[ -n "${!ev:-}" ]]; then
    say "FAIL: env ${ev} is set; sealed run forbids Odds / Railway / prod DB (value not printed)"
    RUN_RC=1
    printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
    imv_seal "${RUN_RC}"
  fi
done

# ----- S-1: dedicated BASE, never ~/kosedge, never checkout -----
if [[ "${BASE}" != /* ]]; then
  say "FAIL: S-1 --base must be an absolute path"
  RUN_RC=2
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi
if [[ ! -d "${BASE}" ]]; then
  say "FAIL: S-1 --base is not a directory: ${BASE}"
  RUN_RC=2
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi

BASE_REAL="$(cd "${BASE}" && pwd -P)"
KOS_REAL="$(cd "${HOME}/kosedge" 2>/dev/null && pwd -P)"
if [[ -n "${KOS_REAL}" && "${BASE_REAL}" == "${KOS_REAL}" ]]; then
  say "FAIL: S-1 BASE resolves to ~/kosedge (${BASE_REAL}). Use a dedicated worktree. This runner never checkouts."
  RUN_RC=2
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi

REPO="$(git -C "${BASE}" rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "${REPO}" ]]; then
  say "FAIL: S-1 --base is not a git worktree"
  RUN_RC=2
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi
# never cd to ~/kosedge; only BASE
cd "${REPO}" || { say "FAIL: cannot cd BASE"; RUN_RC=2; printf '%s\n' 2 > "${FIXED_OUT}/EXIT_CODE"; imv_seal 2; }

HEAD_NOW="$(git rev-parse --verify HEAD 2>/dev/null)"
if [[ "${HEAD_NOW}" != "${CERT_CANDIDATE}" ]]; then
  say "FAIL: S-1 HEAD ${HEAD_NOW} != pinned ${CERT_CANDIDATE}. No checkout will be performed."
  RUN_RC=1
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi
if [[ -n "$(git status --porcelain)" ]]; then
  say "FAIL: S-1 BASE is dirty — no patches allowed"
  RUN_RC=1
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi
if [[ -n "$(git diff --stat)" || -n "$(git diff --cached --stat)" ]]; then
  say "FAIL: S-1 BASE has a patch (diff or cached)"
  RUN_RC=1
  printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
  imv_seal "${RUN_RC}"
fi
say "BASE_OK ${HEAD_NOW} labelled BASE no_patches"

if git cat-file -t "${AUDIT_SHA}" >/dev/null 2>&1; then
  MB="$(git merge-base "${CERT_CANDIDATE}" "${AUDIT_SHA}")"
  AHEAD="$(git rev-list --count "${AUDIT_SHA}..${CERT_CANDIDATE}")"
  BEHIND="$(git rev-list --count "${CERT_CANDIDATE}..${AUDIT_SHA}")"
  case "${MB}" in ${MERGE_BASE_PREFIX}*) ;; *)
    say "FAIL: merge-base ${MB} !prefix ${MERGE_BASE_PREFIX}"
    RUN_RC=1; printf '%s\n' 1 > "${FIXED_OUT}/EXIT_CODE"; imv_seal 1 ;;
  esac
  if [[ "${AHEAD}" != "${EXPECT_CANDIDATE_AHEAD_OF_AUDIT}" || "${BEHIND}" != "${EXPECT_AUDIT_AHEAD_OF_CANDIDATE}" ]]; then
    say "FAIL: relationship ahead=${AHEAD} behind=${BEHIND} (expected ${EXPECT_CANDIDATE_AHEAD_OF_AUDIT}/${EXPECT_AUDIT_AHEAD_OF_CANDIDATE})"
    RUN_RC=1; printf '%s\n' 1 > "${FIXED_OUT}/EXIT_CODE"; imv_seal 1
  fi
  say "RELATIONSHIP_OK merge-base=${MB} ahead=${AHEAD} behind=${BEHIND}"
else
  say "WARN: audit SHA ${AUDIT_SHA} not in this worktree — relationship check skipped (not a pass)"
fi

# ----- P-b: resolve LATEST (symlink dir OR v1 file pointer) -----
resolve_from_latest() {
  local ptr="$1"
  local name="$2"
  local alt="$3"
  if [[ -z "${ptr}" ]]; then
    return 1
  fi
  if [[ -d "${ptr}" ]]; then
    if [[ -f "${ptr}/${name}" ]]; then printf '%s\n' "${ptr}/${name}"; return 0; fi
    if [[ -n "${alt}" && -f "${ptr}/${alt}" ]]; then printf '%s\n' "${ptr}/${alt}"; return 0; fi
    return 1
  fi
  if [[ -f "${ptr}" ]]; then
    local d
    d="$(tr -d '\n' < "${ptr}")"
    if [[ -f "${d}/${name}" ]]; then printf '%s\n' "${d}/${name}"; return 0; fi
    if [[ -n "${alt}" && -f "${d}/${alt}" ]]; then printf '%s\n' "${d}/${alt}"; return 0; fi
  fi
  return 1
}

if [[ -z "${IMV_MANIFEST:-}" ]]; then
  IMV_MANIFEST="$(resolve_from_latest "${PRESTAGE_LATEST}" "imv-manifest.tsv" "imv-w7-manifest.tsv")"
fi
if [[ -z "${IMV_FEATURE_STORE:-}" ]]; then
  if [[ -d "${FEATURE_LATEST_DEFAULT}" ]]; then
    IMV_FEATURE_STORE="${FEATURE_LATEST_DEFAULT}"
  elif [[ -f "${FEATURE_LATEST_DEFAULT}" ]]; then
    IMV_FEATURE_STORE="$(tr -d '\n' < "${FEATURE_LATEST_DEFAULT}")"
  fi
fi

SCRIPT_SHA="$(sha256_file "${SCRIPT_PATH}")"
STARTED_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export REPO BASE FIXED_OUT CERT_CANDIDATE MODE MODEL_VERSION
export STAMP_FULL_PIPELINE_SIMS STAMP_HISTORICAL_SIMS STAMP_BOOTSTRAP_SEED STAMP_BLEND_WEIGHT
export W8_FIRST_KICKOFF_UTC W6_FINALS_SOURCE APPROVAL STARTED_UTC
export IMV_MANIFEST="${IMV_MANIFEST:-}"
export IMV_FEATURE_STORE="${IMV_FEATURE_STORE:-}"
export IMV_FEATURE_STORE_SHA="${IMV_FEATURE_STORE_SHA:-}"
export IMV_HELPER_DIR="${SCRIPT_DIR}"
export SCRIPT_SHA

{
  echo "{"
  echo "  \"script_id\": \"${SCRIPT_ID}\","
  echo "  \"mode\": \"${MODE}\","
  echo "  \"approval\": \"${APPROVAL}\","
  echo "  \"validates_candidate\": \"${CERT_CANDIDATE}\","
  echo "  \"base\": \"${BASE_REAL}\","
  echo "  \"s1_not_kosedge_home\": true,"
  echo "  \"model_version\": \"${MODEL_VERSION}\","
  echo "  \"sim_count_full_pipeline\": ${STAMP_FULL_PIPELINE_SIMS},"
  echo "  \"seed\": ${STAMP_BOOTSTRAP_SEED},"
  echo "  \"blend_weight_documented\": ${STAMP_BLEND_WEIGHT},"
  echo "  \"protocol\": \"${PROTOCOL}\","
  echo "  \"imv_manifest\": \"${IMV_MANIFEST}\","
  echo "  \"imv_feature_store\": \"${IMV_FEATURE_STORE}\","
  echo "  \"imv_feature_store_sha_pin\": \"${IMV_FEATURE_STORE_SHA}\","
  echo "  \"pythondontwritebytecode\": \"${PYTHONDONTWRITEBYTECODE}\","
  echo "  \"git_optional_locks\": \"${GIT_OPTIONAL_LOCKS}\","
  echo "  \"script_sha256\": \"${SCRIPT_SHA}\","
  echo "  \"started_utc\": \"${STARTED_UTC}\","
  echo "  \"execution_utc\": \"${STARTED_UTC}\""
  echo "}"
} > "${FIXED_OUT}/executor-identity.json"
cp "${FIXED_OUT}/executor-identity.json" "${FIXED_OUT}/execution-stamp.json"

{
  echo "HEAD=$(git rev-parse HEAD)"
  echo "BASE=${BASE_REAL}"
  git status --porcelain=v2 --untracked-files=all --branch
} > "${FIXED_OUT}/git-status-before.txt"
printf '%s\n' "${CERT_CANDIDATE}" > "${FIXED_OUT}/CANDIDATE"
printf '%s\n' "${HEAD_NOW}" > "${FIXED_OUT}/HEAD"
printf '%s\n' "${MODE}" > "${FIXED_OUT}/MODE"
printf '%s\n' "${BASE_REAL}" > "${FIXED_OUT}/BASE"

python3 - <<'PY'
import csv, hashlib, json, os, sys
from datetime import datetime, timezone

helper_dir = os.environ.get("IMV_HELPER_DIR") or ""
if helper_dir and helper_dir not in sys.path:
    sys.path.insert(0, helper_dir)
try:
    import nfl_imv_v21 as v21  # type: ignore
except Exception as exc:
    sys.stderr.write("FAIL: C-1..C-8 helper missing: %s\n" % exc)
    sys.exit(1)

out = os.environ["FIXED_OUT"]
repo = os.environ["REPO"]
base = os.environ["BASE"]
candidate = os.environ["CERT_CANDIDATE"]
model = os.environ["MODEL_VERSION"]
mode = os.environ["MODE"]
started = os.environ["STARTED_UTC"]
cap = datetime.now(timezone.utc).replace(microsecond=0)
capture_ts = cap.strftime("%Y-%m-%dT%H:%M:%SZ")
manifest_path = (os.environ.get("IMV_MANIFEST") or "").strip()
feature_store = (os.environ.get("IMV_FEATURE_STORE") or "").strip()
w8_first = os.environ["W8_FIRST_KICKOFF_UTC"]

W4 = [
    "2026-W04-ARI@NYG","2026-W04-ATL@NO","2026-W04-DAL@HOU","2026-W04-DEN@SF",
    "2026-W04-DET@CAR","2026-W04-GB@TB","2026-W04-IND@WAS","2026-W04-JAX@CIN",
    "2026-W04-KC@LV","2026-W04-LAR@PHI","2026-W04-LAC@SEA","2026-W04-MIA@MIN",
    "2026-W04-NE@BUF","2026-W04-NYJ@CHI","2026-W04-PIT@CLE","2026-W04-TEN@BAL",
]
W5 = [
    "2026-W05-BAL@ATL","2026-W05-BUF@LAR","2026-W05-CHI@GB","2026-W05-CIN@MIA",
    "2026-W05-CLE@NYJ","2026-W05-DEN@LAC","2026-W05-DET@ARI","2026-W05-HOU@TEN",
    "2026-W05-IND@PIT","2026-W05-LV@NE","2026-W05-MIN@NO","2026-W05-NYG@WAS",
    "2026-W05-PHI@JAX","2026-W05-SF@SEA","2026-W05-TB@DAL",
]
W6 = [
    "2026-W06-ARI@LAR","2026-W06-BAL@CLE","2026-W06-BUF@LV","2026-W06-CAR@PHI",
    "2026-W06-CHI@ATL","2026-W06-DAL@GB","2026-W06-HOU@JAX","2026-W06-LAC@KC",
    "2026-W06-NO@NYG","2026-W06-NYJ@NE","2026-W06-PIT@TB","2026-W06-SEA@DEN",
    "2026-W06-TEN@IND","2026-W06-WAS@SF",
]
W8 = [
    "2026-W08-ARI@DAL","2026-W08-ATL@TB","2026-W08-BAL@BUF","2026-W08-CAR@GB",
    "2026-W08-CHI@SEA","2026-W08-CLE@PIT","2026-W08-IND@JAX","2026-W08-KC@DEN",
    "2026-W08-LAC@LAR","2026-W08-LV@NYJ","2026-W08-MIN@DET","2026-W08-NE@MIA",
    "2026-W08-PHI@WAS","2026-W08-TEN@CIN",
]
PACK = os.path.join(repo, "apps/web/lib/nfl-canonical-schedule-2026.json")
FORBIDDEN = {
    "edge", "edge_pts", "edge_points", "edge_prob", "edge_ev",
    "play", "lean", "stake", "publish_tag", "action",
}

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def parse_iso(s):
    s = (s or "").strip()
    if s.endswith(".000Z"):
        s = s[:-5] + "Z"
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(timezone.utc)

def parse_num(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.upper() in {"NA", "NAN", "NULL", "NONE"}:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

def canon(t):
    t = (t or "").strip().upper()
    return {"LA": "LAR", "WSH": "WAS"}.get(t, t)

def strip_forbidden(row):
    for k in list(row.keys()):
        if k in FORBIDDEN or k.startswith("edge_") or k.startswith("play"):
            del row[k]
    return row

blocked = []
flags_global = []
inputs = []
files_by_role = {}

# pack
pack_games = {}
if os.path.isfile(PACK):
    pack = json.load(open(PACK, encoding="utf-8"))
    inputs.append({"role": "schedule_pack_2026", "path": PACK, "sha256": sha(PACK), "as_of": pack.get("as_of")})
    for g in pack.get("games") or []:
        pack_games[g.get("game_id")] = g
else:
    blocked.append("canonical 2026 schedule pack missing in BASE")

# P-b manifest (local files only)
if manifest_path:
    if not os.path.isfile(manifest_path):
        blocked.append("IMV_MANIFEST not a file (P-b): %s" % manifest_path)
    else:
        inputs.append({"role": "manifest", "path": manifest_path, "sha256": sha(manifest_path)})
        for raw in open(manifest_path, encoding="utf-8"):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split("\t")
            if len(parts) < 4:
                blocked.append("manifest line needs sha\\tpath\\trole\\tas_of")
                continue
            h, path, role, as_of = parts[0], parts[1], parts[2], parts[3]
            fp = path if os.path.isabs(path) else os.path.join(os.path.dirname(manifest_path), path)
            rec = {"role": role, "path": fp, "expected_sha256": h, "as_of": as_of}
            if not os.path.isfile(fp):
                rec["status"] = "MISSING"
                blocked.append("missing local file %s" % fp)
            else:
                got = sha(fp)
                rec["sha256"] = got
                rec["status"] = "OK" if got == h.lower() else "SHA_MISMATCH"
                if rec["status"] != "OK":
                    blocked.append("sha mismatch %s" % fp)
                files_by_role.setdefault(role, []).append(rec)
            inputs.append(rec)
else:
    flags_global.append("no IMV_MANIFEST — P-b LATEST did not resolve; nflverse files required")
    blocked.append("BLOCKED: no pre-stage manifest. Run nfl-imv-prestage-nflverse.sh then set IMV_MANIFEST or LATEST symlink.")

# feature store — C-1 pin
feat_by_gid = {}
feat_flags = {}
store_pin = (os.environ.get("IMV_FEATURE_STORE_SHA") or "").strip()
from pathlib import Path as _P
if feature_store:
    pin_res = v21.assert_feature_store_pin(_P(feature_store), store_pin or None)
    inputs.append({"role": "feature_store", "path": feature_store, "pin": pin_res})
    if pin_res.get("status") != "OK":
        blocked.append("BLOCKED: C-1 feature-store sha %s (got=%s expected=%s)" % (
            pin_res.get("reason"), pin_res.get("got"), pin_res.get("expected")))
        flags_global.append("FEATURE_STORE_SHA_%s" % pin_res.get("reason"))
    feat_jsonl = str(_P(feature_store) / "features.jsonl") if _P(feature_store).is_dir() else ""
    if feat_jsonl and os.path.isfile(feat_jsonl):
        inputs.append({"role": "features_jsonl", "path": feat_jsonl, "sha256": sha(feat_jsonl)})
        for line in open(feat_jsonl, encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                gid = row.get("game_id_product") or row.get("game_id")
                if gid:
                    feat_by_gid[gid] = row
    flag_path = str(_P(feature_store) / "feature-flags.jsonl") if _P(feature_store).is_dir() else ""
    if flag_path and os.path.isfile(flag_path):
        inputs.append({"role": "feature_flags", "path": flag_path, "sha256": sha(flag_path)})
        for line in open(flag_path, encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                feat_flags.setdefault(row.get("game_id_product") or row.get("game_id") or "_", []).append(row)
    if not feat_by_gid:
        flags_global.append("FEATURE_STORE_EMPTY — see nfl-imv-feature-path-v2.1.md; do not invent features")
else:
    flags_global.append("NO_FEATURE_STORE — model cannot run without file-backed nflverse features")
    blocked.append("BLOCKED: C-1 no feature store to pin")

# W6/W7 finals from nflverse games.csv or w6_finals
def ingest_finals(csv_path):
    out_map = {}
    for row in csv.DictReader(open(csv_path, encoding="utf-8")):
        try:
            season = int(row.get("season") or 0)
            week = int(row.get("week") or 0)
        except ValueError:
            continue
        if season != 2026:
            continue
        gt = str(row.get("game_type") or "REG").upper()
        if gt not in {"REG", "REGULAR"}:
            continue
        gid = "2026-W%02d-%s@%s" % (week, canon(row.get("away_team")), canon(row.get("home_team")))
        hs, a_s = parse_num(row.get("home_score")), parse_num(row.get("away_score"))
        out_map[gid] = {
            "game_id_product": gid,
            "game_id_nflverse": row.get("game_id"),
            "week": week,
            "home_score": hs,
            "away_score": a_s,
            "final": hs is not None and a_s is not None,
            "home_rest": parse_num(row.get("home_rest")),
            "away_rest": parse_num(row.get("away_rest")),
            "roof": row.get("roof"),
            "surface": row.get("surface"),
            "div_game": row.get("div_game"),
            "spread_line": parse_num(row.get("spread_line")),
            "total_line": parse_num(row.get("total_line")),
            "source": "nflverse",
        }
    return out_map

nv_games = {}
for rec in files_by_role.get("schedule_games_csv", []) + files_by_role.get("w6_finals", []):
    fp = rec.get("path")
    if fp and fp.endswith(".csv"):
        nv_games.update(ingest_finals(fp))

# required finals
if mode == "retrospective-w4w6":
    need_finals = W4 + W5 + W6
    slate = W4 + W5 + W6
    record_class = "RETROSPECTIVE"
    snapshot_kind = "RETROSPECTIVE-RESEARCH"
elif mode == "w8-pregame":
    need_finals = W6 + [g for g in nv_games if g.startswith("2026-W07-")]
    # require all 14 W6; W7 also required for W8 lag
    w7_needed = [gid for gid, g in pack_games.items() if g.get("week") == 7]
    need_finals = W6 + w7_needed
    slate = W8
    record_class = "PROSPECTIVE-RESEARCH"
    snapshot_kind = "MODEL-ONLY"
else:
    need_finals, slate = [], []
    record_class, snapshot_kind = "UNKNOWN", "UNKNOWN"
    blocked.append("unknown mode")

missing_finals, not_final = [], []
for gid in need_finals:
    rec = nv_games.get(gid)
    if rec is None:
        missing_finals.append(gid)
    elif not rec.get("final"):
        not_final.append(gid)
if missing_finals:
    blocked.append("BLOCKED: nflverse finals missing %s. Do not invent scores." % missing_finals)
if not_final:
    blocked.append("BLOCKED: nflverse games not final %s. Do not invent scores." % not_final)

# attempt BASE model (file-backed only). Never silent-default.
model_mod = None
sim_fn = None
Inputs = None
import_err = None
if feat_by_gid:
    sys.path.insert(0, os.path.join(base, "services", "model-service"))
    try:
        from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # type: ignore
        Inputs = NflGameInputs
        sim_fn = simulate_nfl_game
        model_mod = "imported"
    except Exception as e:
        import_err = "%s: %s" % (type(e).__name__, e)
        flags_global.append("MODEL_IMPORT_FAILED %s" % import_err)
        # do not invent numbers
else:
    flags_global.append("MODEL_NOT_CALLED_NO_FEATURE_STORE")

# C-7: HFA from pinned BASE, assert == 1.05. Do not hardcode.
hfa_pin = v21.read_and_assert_hfa(__import__("pathlib").Path(base))
if not hfa_pin.get("ok"):
    flags_global.append(str(hfa_pin.get("flag") or "HFA_UNDECLARED"))
    blocked.append("BLOCKED: C-7 HFA %s" % (hfa_pin.get("reason") or hfa_pin.get("flag")))
    sim_fn = None
    Inputs = None

def try_sim(gid, feat):
    """Return (means_dict|None, flags). Never apply rest=7, injury=0, index=1."""
    fl = list(feat_flags.get(gid) or [])
    if sim_fn is None or Inputs is None:
        fl.append({"flag": "MODEL_NOT_IMPORTED", "game_id_product": gid})
        return None, fl
    rest_h = parse_num(feat.get("home_rest_days") or feat.get("rest_days_home"))
    rest_a = parse_num(feat.get("away_rest_days") or feat.get("rest_days_away"))
    if rest_h is None or rest_a is None:
        fl.append({"flag": "FLAG_MISSING_REST", "game_id_product": gid, "forbidden_default": 7.0})
        return None, fl
    epa_ok = all(parse_num(feat.get(k)) is not None for k in (
        "home_off_epa_5g", "away_off_epa_5g", "home_def_epa_allowed_5g", "away_def_epa_allowed_5g"
    ))
    if not epa_ok:
        fl.append({"flag": "FLAG_MISSING_EPA", "game_id_product": gid})
        return None, fl
    off_h = parse_num(feat.get("offense_index_home"))
    off_a = parse_num(feat.get("offense_index_away"))
    def_h = parse_num(feat.get("defense_index_home"))
    def_a = parse_num(feat.get("defense_index_away"))
    if None in (off_h, off_a, def_h, def_a):
        fl.append({"flag": "FLAG_MISSING_TRUE_PR_PRIOR", "game_id_product": gid, "forbidden_default": 1.0})
        return None, fl
    # C-4: injury ALLOWED-FLAGGED. explicit_zero removed. Never map injuries_2026.
    inj = v21.injury_allowed_flagged(feat)
    for flag in inj["flags"]:
        fl.append({"flag": flag, "game_id_product": gid, "injury_handling": inj["injury_handling"]})
    if "FLAG_RAW_INJURIES_2026_REFUSED" in inj["flags"] or "FLAG_IMPUTED_INJURY_DEFAULT" in inj["flags"]:
        # still call only with nulls; imputation never enters the sim
        pass
    intl = bool((pack_games.get(gid) or {}).get("international"))
    if intl:
        fl.append({"flag": "FLAG_HFA_ON_NEUTRAL", "game_id_product": gid})
        return None, fl
    kwargs = {
        "game_id": gid,
        "home_team": feat.get("home_team") or (pack_games.get(gid) or {}).get("home_team_id"),
        "away_team": feat.get("away_team") or (pack_games.get(gid) or {}).get("away_team_id"),
        "offense_index_home": off_h,
        "offense_index_away": off_a,
        "defense_index_home": def_h,
        "defense_index_away": def_a,
        "rest_days_home": rest_h,
        "rest_days_away": rest_a,
        "home_off_epa_5g": parse_num(feat.get("home_off_epa_5g")),
        "away_off_epa_5g": parse_num(feat.get("away_off_epa_5g")),
        "home_def_epa_allowed_5g": parse_num(feat.get("home_def_epa_allowed_5g")),
        "away_def_epa_allowed_5g": parse_num(feat.get("away_def_epa_allowed_5g")),
        "injury_nowcast_impact_home": None,
        "injury_nowcast_impact_away": None,
    }
    kwargs.update(inj["pass_to_sim"])
    try:
        proj = sim_fn(
            Inputs(**kwargs),
            simulations=int(os.environ["STAMP_FULL_PIPELINE_SIMS"]),
            seed=int(os.environ["STAMP_BOOTSTRAP_SEED"]),
            model_version=model,
            market_spread_home=None,
            market_total=None,
        )
    except Exception as e:
        fl.append({"flag": "MODEL_CALL_FAILED", "detail": "%s: %s" % (type(e).__name__, e), "game_id_product": gid})
        return None, fl
    mk = proj.get("markets") if isinstance(proj, dict) else None
    if not isinstance(mk, dict):
        mk = {}
    means = {
        "model_spread_home": parse_num(mk.get("spread_home") or proj.get("spread_home") or proj.get("expected_margin_home")),
        "model_total": parse_num(mk.get("total") or proj.get("total_mean") or proj.get("expected_total")),
        "model_home_win_prob": parse_num(mk.get("home_win_prob") or proj.get("home_win_prob")),
        "hfa_declared": True,
        "hfa_points_applied": hfa_pin["hfa_points"],
        "hfa_source": hfa_pin["hfa_source"],
        "model_execution": v21.model_execution_label(executed=True),
    }
    return means, fl

rows_spread, rows_total, rows_ml = [], [], []
excluded = []
any_null = False
called = 0

for gid in slate:
    g = pack_games.get(gid) or {}
    # C-5: missing kickoff → BLOCKED, no w8_first fallback (any mode).
    ko = v21.require_kickoff(g.get("kickoff_utc"), game_id=gid)
    if not ko["ok"]:
        blocked.append("BLOCKED: %s %s (no fallback)" % (ko["flag"], gid))
        flags_global.append(str(ko["flag"]))
    elif mode == "w8-pregame":
        try:
            if parse_iso(ko["kickoff_utc"]) <= parse_iso(capture_ts):
                excluded.append({"game_id": gid, "kickoff_utc": ko["kickoff_utc"], "reason": "kickoff_at_or_before_seal"})
                continue
        except Exception:
            blocked.append("BLOCKED: BLOCKED_UNPARSEABLE_KICKOFF %s (no fallback)" % gid)
    feat = feat_by_gid.get(gid) or {}
    nv = nv_games.get(gid) or {}
    means, fl = try_sim(gid, feat)
    called += 1 if means else 0
    # C-6: parse W## — never gid[8:10] ("-A" on 2026-W04-…).
    week = v21.parse_product_week(gid, g.get("week"))
    if week is None:
        blocked.append("BLOCKED: FLAG_MISSING_WEEK %s" % gid)
        fl.append({"flag": "FLAG_MISSING_WEEK", "game_id_product": gid})
    if week is not None and week <= 4 and mode == "retrospective-w4w6":
        fl.append({"flag": "SUPERVISED_SKIPPED_WEEK_LE_4", "game_id_product": gid})
    rest_def = parse_num((feat or {}).get("home_rest_days")) is None and parse_num(nv.get("home_rest")) is None
    inj = v21.injury_allowed_flagged(feat)
    for flag in inj["flags"]:
        fl.append({"flag": flag, "game_id_product": gid})
    src_weeks = feat.get("source_weeks") or (feat.get("as_of") or {}).get("source_weeks") or []
    as_of = v21.record_as_of_check(
        game_id=gid,
        game_week=week,
        source_weeks=src_weeks,
        kickoff_utc=g.get("kickoff_utc"),
        feature_as_of_week=feat.get("as_of_week"),
    )
    if as_of.status != "PASS":
        blocked.append("BLOCKED: C-2 as-of %s %s" % (gid, as_of.flags))
        means = None
        any_null = True
    for flag in as_of.flags:
        fl.append({"flag": flag, "game_id_product": gid})
    venue_def = not (g.get("venue") or nv.get("roof"))
    base_row = {
        "record_class": record_class,
        "split": "2026_W4W6_RETRO" if mode == "retrospective-w4w6" else "2026_W8_PREGAME",
        "season": 2026,
        "week": week,
        "game_type": "REG",
        "game_id_product": gid,
        "game_id_nflverse": nv.get("game_id_nflverse"),
        "home_team": g.get("home_team_id"),
        "away_team": g.get("away_team_id"),
        "kickoff_utc": g.get("kickoff_utc"),
        "capture_ts": capture_ts,
        "execution_utc": started,
        "code_sha": candidate,
        "model_version": model,
        "base": base,
        "snapshot_kind": snapshot_kind,
        "publish": False,
        "hand_entered_news": False,
        "defaulted_rest": rest_def,
        "defaulted_injury": False,
        "injury_handling": inj["injury_handling"],
        "injury_source": inj["injury_source"],
        "home_injury_impact": None,
        "away_injury_impact": None,
        "diff_injury_impact": None,
        "as_of": as_of.to_dict(),
        "as_of_week": as_of.as_of_week,
        "source_weeks": as_of.source_weeks,
        "defaulted_venue": venue_def,
        "feature_flags": fl,
        "w6_finals_source": "nflverse",
    }
    if rest_def:
        base_row["flag_defaulted_rest"] = True
    base_row["flag_missing_injury_input"] = True
    if venue_def:
        base_row["flag_defaulted_venue"] = True
    if means and as_of.status == "PASS":
        base_row.update(means)
    else:
        base_row["model_spread_home"] = None
        base_row["model_total"] = None
        base_row["model_home_win_prob"] = None
        base_row["model_execution"] = v21.model_execution_label(executed=False)
        base_row["model_number_reason"] = "BLOCKED_NO_MODEL_EXECUTION"
        any_null = True
    if mode == "w8-pregame":
        # MODEL-ONLY: do not copy nflverse lines into the row
        pass
    else:
        # RETROSPECTIVE grading attachment only (not a play)
        if nv.get("final"):
            base_row["actual_home_score"] = nv.get("home_score")
            base_row["actual_away_score"] = nv.get("away_score")
        if nv.get("spread_line") is not None:
            base_row["market_close_nflverse_spread"] = nv.get("spread_line")
            base_row["market_close_source"] = "nflverse"
        if nv.get("total_line") is not None:
            base_row["market_close_nflverse_total"] = nv.get("total_line")
    for mkt, bucket in (("spread", rows_spread), ("total", rows_total), ("ml", rows_ml)):
        row = strip_forbidden(dict(base_row))
        row["market"] = mkt
        bucket.append(row)
        if row.get("model_spread_home") is None or row.get("model_total") is None or row.get("model_home_win_prob") is None:
            any_null = True

if any_null:
    blocked.append("BLOCKED: null model output (model_spread_home/model_total/model_home_win_prob). e0bdcc1a: null forces BLOCKED. No invented numbers.")
    flags_global.append("NULL_MODEL_OUTPUT_FORCES_BLOCKED")

status = "BLOCKED" if blocked else "SEAL"
label = "BLOCKED" if blocked else ("RETROSPECTIVE" if mode == "retrospective-w4w6" else "MODEL-ONLY")

fp_doc = {
    "capture_ts": capture_ts,
    "execution_utc": started,
    "model_version": model,
    "code_sha": candidate,
    "base": base,
    "inputs": inputs,
    "feature_store": feature_store or None,
    "model_import": model_mod,
    "model_import_error": import_err,
    "model_calls_attempted_ok": called,
}
open(os.path.join(out, "input-fingerprints.json"), "w").write(json.dumps(fp_doc, indent=2) + "\n")
doc = {
    "mode": mode,
    "record_class": record_class,
    "snapshot_kind": snapshot_kind,
    "approval": os.environ.get("APPROVAL"),
    "validates_candidate": candidate,
    "base": base,
    "s1": "dedicated_worktree_no_checkout_no_patches",
    "capture_ts": capture_ts,
    "execution_utc": started,
    "w8_first_kickoff_utc": w8_first if mode == "w8-pregame" else None,
    "publish": False,
    "frozen_once_sealed": True,
    "re_run_is_new_snapshot": True,
    "null_model_forces_blocked": True,
    "blocked_no_model_execution": True,
    "hfa_pin": hfa_pin,
    "c8_pythondontwritebytecode": os.environ.get("PYTHONDONTWRITEBYTECODE"),
    "c8_git_optional_locks": os.environ.get("GIT_OPTIONAL_LOCKS"),
    "status": status,
    "label": label,
    "blocked": blocked,
    "missing_finals": missing_finals,
    "not_final": not_final,
    "excluded_games_kickoff_le_seal": excluded,
    "row_counts": {"spread": len(rows_spread), "total": len(rows_total), "ml": len(rows_ml)},
    "flags_global": flags_global,
    "p_b_manifest": manifest_path or None,
    "feature_store": feature_store or None,
    "config_stamp": {
        "model_version": model,
        "sim_count": int(os.environ["STAMP_FULL_PIPELINE_SIMS"]),
        "seed": int(os.environ["STAMP_BOOTSTRAP_SEED"]),
        "blend_weight_documented": float(os.environ["STAMP_BLEND_WEIGHT"]),
        "code_sha": candidate,
        "execution_utc": started,
        "capture_ts": capture_ts,
    },
}
open(os.path.join(out, "run-report.json"), "w").write(json.dumps(doc, indent=2) + "\n")
open(os.path.join(out, "LABEL"), "w").write(label + "\n")
open(os.path.join(out, "RECORD_CLASS"), "w").write(record_class + "\n")
open(os.path.join(out, "CAPTURE_TS"), "w").write(capture_ts + "\n")
open(os.path.join(out, "SNAPSHOT_KIND"), "w").write(snapshot_kind + "\n")
open(os.path.join(out, "FROZEN"), "w").write("sealed_at=%s re_run_is_new_snapshot=true\n" % capture_ts)
for name, rows in (("spread", rows_spread), ("total", rows_total), ("ml", rows_ml)):
    with open(os.path.join(out, "sealed_rows_%s.jsonl" % name), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(strip_forbidden(r), separators=(",", ":")) + "\n")
print("STATUS=" + status)
print("LABEL=" + label)
print("CAPTURE_TS=" + capture_ts)
print("NULL_FORCES_BLOCKED=" + str(any_null).lower())
sys.exit(6 if status == "BLOCKED" else 0)
PY
PY_RC=$?

say "python_rc=${PY_RC}"
if [[ "${PY_RC}" -eq 6 ]]; then
  say "BLOCKED (null model or missing nflverse/features). Snapshot will still seal (P-a)."
  RUN_RC=6
elif [[ "${PY_RC}" -ne 0 ]]; then
  say "FAIL: python rc=${PY_RC} — still sealing (P-a)"
  RUN_RC=1
else
  RUN_RC=0
  say "SEAL ${FIXED_OUT}"
fi

{
  echo "HEAD=$(git rev-parse HEAD)"
  echo "BASE=$(pwd -P)"
  git status --porcelain=v2 --untracked-files=all --branch
} > "${FIXED_OUT}/git-status-after.txt"
if ! cmp -s "${FIXED_OUT}/git-status-before.txt" "${FIXED_OUT}/git-status-after.txt"; then
  say "FAIL: BASE worktree changed (S-1 no patches)"
  RUN_RC=1
fi
printf '%s\n' "${RUN_RC}" > "${FIXED_OUT}/EXIT_CODE"
say "EXIT_CODE ${RUN_RC}"
imv_seal "${RUN_RC}"
