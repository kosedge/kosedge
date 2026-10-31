#!/usr/bin/env bash
# nfl-imv-prestage-nflverse.sh
# t4139u — SEPARATE pre-stage fetch. NOT part of the sealed run.
# Network is allowed here. The sealed runner (nfl-imv-sealed-v1.sh) is network-denied
# and must only read the files this script writes.
#
# Ryan named nflverse as the read-only public source for W6 finals.
# This step downloads the current `schedules` release assets that contain
# 2026 W6 finals AND the 2026 schedule. It does not fetch injuries, odds,
# Railway, or a prod DB. It does not invent scores.
#
# Exact files (living release tag `schedules`; there is no sched_2026.csv asset):
#   https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv
#   https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet
#   https://github.com/nflverse/nflverse-data/releases/download/schedules/timestamp.json
#   https://github.com/nflverse/nflverse-data/releases/download/schedules/timestamp.txt
# Release page:
#   https://github.com/nflverse/nflverse-data/releases/tag/schedules
# Maintainer upstream (do not pin as sealed SoT; nflreadpy uses the release):
#   https://github.com/nflverse/nfldata/blob/master/data/games.csv
#
# Usage (Ryan's Mac, BEFORE the sealed W7 run, BEFORE 2026-10-23T00:15Z):
#   bash /opt/cursor/artifacts/nfl-imv-prestage-nflverse.sh
# Then:
#   IMV_W7_MANIFEST=/var/tmp/nfl-imv-prestage-nflverse/LATEST/imv-w7-manifest.tsv \
#     ./nfl-imv-sealed-v1.sh w7-pregame
#
# Per file this script records: release tag, release id, exact URL,
# retrieval_utc, data_cutoff, sha256.

set -euo pipefail

SCRIPT_ID="nfl-imv-prestage-nflverse"
RELEASE_TAG="schedules"
RELEASE_API="https://api.github.com/repos/nflverse/nflverse-data/releases/tags/${RELEASE_TAG}"
UA="kosedge-imv-prestage/t4139u"
OUT_BASE="/var/tmp/nfl-imv-prestage-nflverse"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${IMV_PRESTAGE_OUT:-${OUT_BASE}/${STAMP}}"
RETRIEVAL_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Product W6 slate (canonical pack). nflverse Rams = LA.
W6_PRODUCT=(
  "2026-W06-ARI@LAR" "2026-W06-BAL@CLE" "2026-W06-BUF@LV" "2026-W06-CAR@PHI"
  "2026-W06-CHI@ATL" "2026-W06-DAL@GB" "2026-W06-HOU@JAX" "2026-W06-LAC@KC"
  "2026-W06-NO@NYG" "2026-W06-NYJ@NE" "2026-W06-PIT@TB" "2026-W06-SEA@DEN"
  "2026-W06-TEN@IND" "2026-W06-WAS@SF"
)

mkdir -p "${OUT}/files"
: > "${OUT}/console.log"
say() { printf '%s\n' "$*" | tee -a "${OUT}/console.log" >&2; }

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

say "${SCRIPT_ID} out=${OUT} retrieval_utc=${RETRIEVAL_UTC}"
say "THIS IS NOT THE SEALED RUN. Network allowed. Injuries are not fetched."

# --- release metadata (tag / version) ---
curl -fsSL -A "${UA}" -o "${OUT}/files/github-release-schedules.json" "${RELEASE_API}"
python3 - <<PY
import json, os, sys
from datetime import datetime, timezone
out = "${OUT}"
d = json.load(open(os.path.join(out, "files", "github-release-schedules.json"), encoding="utf-8"))
if d.get("message") == "Not Found":
    sys.stderr.write("FAIL: GitHub release tag schedules not found\n")
    sys.exit(2)
meta = {
    "source": "nflverse",
    "approval": "t4139u Ryan named nflverse as read-only W6 finals source",
    "release_tag": d.get("tag_name"),
    "release_name": d.get("name"),
    "release_id": d.get("id"),
    "html_url": d.get("html_url"),
    "published_at": d.get("published_at"),
    "updated_at": d.get("updated_at"),
    "target_commitish": d.get("target_commitish"),
    "retrieval_utc": "${RETRIEVAL_UTC}",
}
open(os.path.join(out, "release-metadata.json"), "w").write(json.dumps(meta, indent=2) + "\n")
print("RELEASE_TAG=" + str(meta["release_tag"]))
print("RELEASE_ID=" + str(meta["release_id"]))
print("RELEASE_UPDATED_AT=" + str(meta["updated_at"]))
PY

# Exact assets required for W6 finals + 2026 schedule.
# sched_2026.csv / sched_2026.parquet are NOT on this release (verified 2026-10-22).
declare -a FILES=(
  "games.csv|https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv|schedule_games_csv"
  "games.parquet|https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet|schedule_games_parquet"
  "timestamp.json|https://github.com/nflverse/nflverse-data/releases/download/schedules/timestamp.json|schedule_timestamp_json"
  "timestamp.txt|https://github.com/nflverse/nflverse-data/releases/download/schedules/timestamp.txt|schedule_timestamp_txt"
)

FILE_RECORDS="${OUT}/file-records.jsonl"
: > "${FILE_RECORDS}"

for spec in "${FILES[@]}"; do
  IFS='|' read -r name url role <<<"${spec}"
  dest="${OUT}/files/${name}"
  say "GET ${url}"
  curl -fsSL -A "${UA}" -o "${dest}" "${url}"
  [[ -s "${dest}" ]] || { say "FAIL: empty download ${name}"; exit 2; }
  h="$(sha256_file "${dest}")"
  bytes="$(wc -c < "${dest}" | tr -d ' ')"
  printf '%s\n' "${h}  ${name}" >> "${OUT}/DOWNLOAD_SHA256"
  python3 - <<PY
import json, os
rec = {
    "name": "${name}",
    "role": "${role}",
    "nflverse_release_tag": "${RELEASE_TAG}",
    "exact_url": "${url}",
    "retrieval_utc": "${RETRIEVAL_UTC}",
    "sha256": "${h}",
    "bytes": int("${bytes}"),
    "path": "${dest}",
}
# fill release_id / data_cutoff after timestamp parse in the next step
open("${FILE_RECORDS}", "a").write(json.dumps(rec) + "\n")
PY
  say "OK ${name} sha256=${h} bytes=${bytes}"
done

# Parse cutoff, extract W6 finals, verify FINAL, write manifest.
export OUT RETRIEVAL_UTC RELEASE_TAG
export W6_CSV="${OUT}/files/games.csv"
python3 - <<'PY'
import csv, json, os, sys
from datetime import datetime, timezone, timedelta

out = os.environ["OUT"]
retrieval = os.environ["RETRIEVAL_UTC"]
tag = os.environ["RELEASE_TAG"]
w6_csv = os.environ["W6_CSV"]

W6 = [
    "2026-W06-ARI@LAR","2026-W06-BAL@CLE","2026-W06-BUF@LV","2026-W06-CAR@PHI",
    "2026-W06-CHI@ATL","2026-W06-DAL@GB","2026-W06-HOU@JAX","2026-W06-LAC@KC",
    "2026-W06-NO@NYG","2026-W06-NYJ@NE","2026-W06-PIT@TB","2026-W06-SEA@DEN",
    "2026-W06-TEN@IND","2026-W06-WAS@SF",
]

def canon(t):
    t = (t or "").strip().upper()
    return {"LA": "LAR", "WSH": "WAS"}.get(t, t)

def parse_num(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.upper() in {"NA", "NAN", "NULL", "NONE"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None

# data cutoff: timestamp.json last_updated (nflverse local clock) → UTC
ts_json = json.load(open(os.path.join(out, "files", "timestamp.json"), encoding="utf-8"))
raw_cutoff = (ts_json.get("last_updated") or "").strip()
# expected like "2026-10-22 10:43:22 EDT"
data_cutoff_utc = None
data_cutoff_raw = raw_cutoff
try:
    parts = raw_cutoff.rsplit(" ", 1)
    if len(parts) == 2:
        naive, tzname = parts
        dt = datetime.strptime(naive, "%Y-%m-%d %H:%M:%S")
        off = {"EDT": -4, "EST": -5, "CDT": -5, "CST": -6, "MDT": -6, "MST": -7, "PDT": -7, "PST": -8, "UTC": 0, "GMT": 0}.get(tzname)
        if off is not None:
            data_cutoff_utc = (dt - timedelta(hours=off)).replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
except Exception:
    data_cutoff_utc = None
if not data_cutoff_utc:
    data_cutoff_utc = retrieval
    data_cutoff_note = "timestamp parse failed; using retrieval_utc"
else:
    data_cutoff_note = "nflverse timestamp.json last_updated converted to UTC"

rel = json.load(open(os.path.join(out, "release-metadata.json"), encoding="utf-8"))
rel["data_cutoff_raw"] = data_cutoff_raw
rel["data_cutoff_utc"] = data_cutoff_utc
rel["data_cutoff_note"] = data_cutoff_note
open(os.path.join(out, "release-metadata.json"), "w").write(json.dumps(rel, indent=2) + "\n")

# rewrite file-records with cutoff + release_id
recs = []
for line in open(os.path.join(out, "file-records.jsonl"), encoding="utf-8"):
    rec = json.loads(line)
    rec["nflverse_release_id"] = rel.get("release_id")
    rec["nflverse_release_updated_at"] = rel.get("updated_at")
    rec["data_cutoff_raw"] = data_cutoff_raw
    rec["data_cutoff_utc"] = data_cutoff_utc
    recs.append(rec)
with open(os.path.join(out, "file-records.jsonl"), "w", encoding="utf-8") as f:
    for rec in recs:
        f.write(json.dumps(rec) + "\n")
open(os.path.join(out, "file-records.json"), "w").write(json.dumps({
    "retrieval_utc": retrieval,
    "data_cutoff_utc": data_cutoff_utc,
    "data_cutoff_raw": data_cutoff_raw,
    "nflverse_release_tag": tag,
    "nflverse_release_id": rel.get("release_id"),
    "files": recs,
    "injuries_fetched": False,
    "lines_fetched": False,
    "note": "Injuries are not in the t4139u approval. Missing injury inputs are flagged in the sealed run, never invented.",
}, indent=2) + "\n")

# extract W6 + W7 schedule rows from games.csv (scores only; no lines)
sha_csv = None
for rec in recs:
    if rec["name"] == "games.csv":
        sha_csv = rec["sha256"]

def product_gid(season, week, away, home):
    return "%d-W%02d-%s@%s" % (int(season), int(week), canon(away), canon(home))

w6_rows = {}
w7_sched = []
with open(w6_csv, newline="", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
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
        away, home = row.get("away_team"), row.get("home_team")
        gid = product_gid(season, week, away, home)
        base = {
            "game_id_product": gid,
            "game_id_nflverse": row.get("game_id"),
            "season": season,
            "week": week,
            "game_type": "REG",
            "away_team_nflverse": away,
            "home_team_nflverse": home,
            "away_team_product": canon(away),
            "home_team_product": canon(home),
            "gameday": row.get("gameday"),
            "gametime": row.get("gametime"),
            "stadium": row.get("stadium"),
            "location": row.get("location"),
            "roof": row.get("roof"),
            "away_rest": row.get("away_rest"),
            "home_rest": row.get("home_rest"),
            "source": "nflverse",
            "source_file": "games.csv",
            "source_sha256": sha_csv,
            # lines intentionally omitted (W7 is MODEL-ONLY)
        }
        if week == 6:
            hs = parse_num(row.get("home_score"))
            a_s = parse_num(row.get("away_score"))
            result = parse_num(row.get("result"))
            is_final = hs is not None and a_s is not None
            rec = dict(base)
            rec.update({
                "home_score": hs,
                "away_score": a_s,
                "result": result,
                "total": parse_num(row.get("total")),
                "overtime": row.get("overtime"),
                "final": is_final,
            })
            w6_rows[gid] = rec
        elif week == 7:
            w7_sched.append(base)

# verify every required W6 game is FINAL
missing = []
not_final = []
for gid in W6:
    rec = w6_rows.get(gid)
    if rec is None:
        missing.append(gid)
    elif not rec.get("final"):
        not_final.append(gid)

status = "BLOCKED" if (missing or not_final) else "READY"
blocked = []
if missing:
    blocked.append("W6 games missing from nflverse games.csv: %s" % missing)
if not_final:
    blocked.append("W6 games present but not final (empty/non-numeric scores): %s" % not_final)

w6_path = os.path.join(out, "w6-finals.jsonl")
with open(w6_path, "w", encoding="utf-8") as f:
    for gid in W6:
        rec = w6_rows.get(gid) or {"game_id_product": gid, "final": False, "missing": True}
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")

open(os.path.join(out, "w7-schedule-nflverse.jsonl"), "w").write(
    "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in w7_sched)
)

# sha of extracted finals
import hashlib
w6_sha = hashlib.sha256(open(w6_path, "rb").read()).hexdigest()
as_of = data_cutoff_utc

# manifest for sealed runner (tab: sha path role as_of)
man = os.path.join(out, "imv-w7-manifest.tsv")
lines = ["# sha256\tpath\trole\tas_of  (t4139u nflverse pre-stage; not sealed)"]
for rec in recs:
    lines.append("%s\t%s\t%s\t%s" % (rec["sha256"], rec["path"], rec["role"], as_of))
lines.append("%s\t%s\tw6_finals\t%s" % (w6_sha, w6_path, as_of))
open(man, "w").write("\n".join(lines) + "\n")

report = {
    "script_id": "nfl-imv-prestage-nflverse",
    "ticket": "t4139u",
    "sealed_run": False,
    "status": status,
    "blocked": blocked,
    "retrieval_utc": retrieval,
    "data_cutoff_raw": data_cutoff_raw,
    "data_cutoff_utc": data_cutoff_utc,
    "nflverse_release_tag": tag,
    "nflverse_release_id": rel.get("release_id"),
    "nflverse_release_updated_at": rel.get("updated_at"),
    "w6_required_n": 14,
    "w6_found_n": len([g for g in W6 if g in w6_rows]),
    "w6_final_n": len([g for g in W6 if w6_rows.get(g, {}).get("final")]),
    "w6_missing": missing,
    "w6_not_final": not_final,
    "w7_schedule_rows": len(w7_sched),
    "injuries_fetched": False,
    "lines_copied": False,
    "manifest": man,
    "note": "If status=BLOCKED the sealed W7 run must also be BLOCKED. Do not invent scores.",
}
open(os.path.join(out, "prestage-report.json"), "w").write(json.dumps(report, indent=2) + "\n")
open(os.path.join(out, "STATUS"), "w").write(status + "\n")
print("PRESTAGE_STATUS=" + status)
print("DATA_CUTOFF_UTC=" + data_cutoff_utc)
print("W6_FINAL_N=" + str(report["w6_final_n"]))
print("MANIFEST=" + man)
if status == "BLOCKED":
    sys.exit(6)
sys.exit(0)
PY
PRE_RC=$?

# pointer for the sealed runner (P-b): symlink dir + text fallback
mkdir -p "${OUT_BASE}"
printf '%s\n' "${OUT}" > "${OUT_BASE}/LATEST.txt"
ln -sfn "${OUT}" "${OUT_BASE}/LATEST"

# SHA256SUMS last (pre-stage integrity; not the W7 seal)
(
  cd "${OUT}"
  find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | while IFS= read -r f; do
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "${f}"; else sha256sum "${f}"; fi
  done
) > "${OUT}/SHA256SUMS"

say "PRESTAGE_RC=${PRE_RC} STATUS=$(cat "${OUT}/STATUS") LATEST=${OUT}"
say "Set IMV_W7_MANIFEST=${OUT}/imv-w7-manifest.tsv for the sealed W7 run."
exit "${PRE_RC}"
