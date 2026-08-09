#!/usr/bin/env bash
# Lightweight daily Roster + Injury Intel → SoT → Integrity Gate → Engine helper.
# Usage:
#   bash scripts/nfl/run_daily_roster_injury_intel.sh            # print checklist path + SoT summary
#   bash scripts/nfl/run_daily_roster_injury_intel.sh --verify   # load pack + assert SoT + integrity gate
#   bash scripts/nfl/run_daily_roster_injury_intel.sh --sim      # gate → small packaged re-sim (5k/200)
#   bash scripts/nfl/run_daily_roster_injury_intel.sh --gate     # integrity gate only (archive snapshot)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PACK="services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
CHECKLIST="scripts/nfl/daily_roster_injury_intel_checklist.md"
DAY="${DAY:-$(date -u +%Y%m%d)}"
REF_DATE="${INTEGRITY_REFERENCE_DATE:-$(date -u +%Y-%m-%d)}"

echo "== Daily roster/injury intel =="
echo "checklist: $CHECKLIST"
echo "SoT pack:  $PACK"
echo "day:       $DAY"
echo "ref_date:  $REF_DATE"
echo

PYBIN="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYBIN" ]]; then PYBIN="$(command -v python3)"; fi
"$PYBIN" - <<'PY'
import json
from pathlib import Path
p = Path("services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json")
d = json.loads(p.read_text())
print(f"snapshot_id={d.get('snapshot_id')}")
print(f"as_of={d.get('as_of')} daily_intel_as_of={d.get('daily_intel_as_of')}")
print(f"skill_rows={d.get('row_count')} ol_roles={len(d.get('ol_roles') or [])} injury_paths={len(d.get('injury_paths') or [])}")
was = [r for r in d.get("rows") or [] if r.get("team") == "WAS"]
for r in sorted(was, key=lambda x: (x["position"], int(x["depth_order"]))):
    st = r.get("injury_status") or "-"
    print(f"  WAS {r['position']}{r['depth_order']} {r['player_name']} [{st}] id={r.get('player_id')}")
ol = [r for r in (d.get("ol_roles") or []) if r.get("team") == "WAS"]
for r in ol:
    print(f"  OL  {r.get('position')}#{r.get('depth_order')} {r.get('player_name')} [{r.get('injury_status','-')}]")
PY

run_gate() {
  echo
  echo "== Data integrity gate (hard-fail) =="
  "$PYBIN" scripts/nfl/run_data_integrity_gate.py \
    --archive \
    --require-archive \
    --reference-date "$REF_DATE" \
    --json-out "data/ops/nfl-data-integrity-gate-${DAY}.json"
}

MODE="${1:-}"
if [[ "$MODE" == "--gate" ]]; then
  run_gate
  echo
  echo "Gate done. Downstream re-sim allowed only after PASS."
  exit 0
fi

if [[ "$MODE" == "--verify" ]]; then
  run_gate
  echo
  echo "== Verify engine SoT path =="
  (
    cd services/model-service
    PYTHONPATH=. NFL_DEPTH_INTEGRITY_FAIL_CLOSED=1 "$PYBIN" - <<'PY'
from src.services.nfl_season_engine.loaders import (
    ROSTER_SOURCE_PACKAGED,
    build_packaged_real_universe,
    load_packaged_depth_chart,
)
rows, meta = load_packaged_depth_chart(2026)
assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
assert meta.get("snapshot_id"), "snapshot_id required on pack meta"
u = build_packaged_real_universe(2026)
assert u.notes.get("roster_source") == ROSTER_SOURCE_PACKAGED
assert u.notes.get("snapshot_id") == meta.get("snapshot_id")
print("ok: packaged SoT exclusive; snapshot_id=", u.notes.get("snapshot_id"))
print("ok: daily_intel_as_of=", u.notes.get("daily_intel_as_of"))
print("ok: ol_roles_count=", u.notes.get("ol_roles_count"))
print("ok: packaged_injury_paths=", len(u.packaged_injury_paths or []))
PY
  )
fi

if [[ "$MODE" == "--sim" ]]; then
  run_gate
  echo
  echo "== Packaged research re-sim (5k team / 200 player) =="
  (
    cd services/model-service
    PYTHONPATH=. NFL_DEPTH_INTEGRITY_FAIL_CLOSED=1 "$PYBIN" ../../scripts/nfl/run_launch_research_sims.py \
      --force-packaged --n-team-sims 5000 --n-player-sims 200 --workers 4
  )
  echo "Write ops note: data/ops/nfl-daily-roster-intel-${DAY}.md (include snapshot_id + gate PASS)"
fi

echo
echo "Next: follow $CHECKLIST → edit SoT → --verify (gate) → --sim → ops note → PR to deploy-vercel"
echo "Phase 2 blocked until integrity gate is green."
