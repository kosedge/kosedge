#!/usr/bin/env bash
# 100k expert-sim candidate launcher (NOT LOCKED).
# Runs launch research then finalize. Safe to invoke under screen/nohup.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1

STAMP_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="data/ops/nfl-100k-expert-sim-candidate-${STAMP_UTC}-run.log"
PROGRESS="data/ops/nfl-100k-expert-sim-candidate-progress.json"
PIDFILE="data/ops/nfl-100k-expert-sim-candidate.pid"
OUTDIR_PTR="data/ops/nfl-100k-expert-sim-candidate-outdir.txt"

WORKERS="${WORKERS:-7}"
N_TEAM="${N_TEAM:-100000}"
N_PLAYER="${N_PLAYER:-1000}"

mkdir -p data/ops
echo $$ > "$PIDFILE"

{
  echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "engine tip=$(git rev-parse --short HEAD)"
  echo "workers=$WORKERS n_team=$N_TEAM n_player=$N_PLAYER"
} | tee -a "$LOG"

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path("$PROGRESS").write_text(json.dumps({
  "status": "running",
  "started_at_utc": datetime.now(timezone.utc).isoformat(),
  "n_team_sims": $N_TEAM,
  "n_player_sims": $N_PLAYER,
  "workers": $WORKERS,
  "pid": $$,
  "log": "$LOG",
}, indent=2) + "\n")
PY

set +e
.venv/bin/python -u scripts/nfl/run_launch_research_sims.py \
  --n-team-sims "$N_TEAM" \
  --n-player-sims "$N_PLAYER" \
  --workers "$WORKERS" \
  --force-packaged \
  --seed 20260809 \
  2>&1 | tee -a "$LOG"
SIM_RC=${PIPESTATUS[0]}
set -e

OUT_DIR="$(grep -E '^DONE bundle=' "$LOG" | tail -1 | sed 's/^DONE bundle=//')"
if [[ -z "${OUT_DIR}" ]]; then
  OUT_DIR="$(ls -dt data/ops/nfl-season-engine-launch-*Nteam${N_TEAM}-Nplayer${N_PLAYER}-* 2>/dev/null | head -1 || true)"
fi
echo "$OUT_DIR" > "$OUTDIR_PTR"
echo "OUT_DIR=$OUT_DIR sim_rc=$SIM_RC" | tee -a "$LOG"

if [[ "$SIM_RC" -ne 0 || -z "$OUT_DIR" || ! -d "$OUT_DIR" ]]; then
  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path("$PROGRESS").write_text(json.dumps({
  "status": "sim_failed",
  "sim_rc": $SIM_RC,
  "out_dir": "$OUT_DIR",
  "updated_at_utc": datetime.now(timezone.utc).isoformat(),
  "log": "$LOG",
}, indent=2) + "\n")
PY
  exit "$SIM_RC"
fi

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path("$PROGRESS").write_text(json.dumps({
  "status": "finalizing",
  "out_dir": "$OUT_DIR",
  "updated_at_utc": datetime.now(timezone.utc).isoformat(),
  "log": "$LOG",
}, indent=2) + "\n")
PY

set +e
.venv/bin/python -u scripts/nfl/finalize_100k_expert_candidate.py \
  --source "$OUT_DIR" \
  2>&1 | tee -a "$LOG"
FIN_RC=${PIPESTATUS[0]}
set -e

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
Path("$PROGRESS").write_text(json.dumps({
  "status": "complete" if $FIN_RC == 0 else "finalize_failed",
  "sim_rc": $SIM_RC,
  "finalize_rc": $FIN_RC,
  "out_dir": "$OUT_DIR",
  "updated_at_utc": datetime.now(timezone.utc).isoformat(),
  "log": "$LOG",
  "locked_snapshot": False,
  "note": "NOT LOCKED — awaiting clearance",
}, indent=2) + "\n")
PY

echo "EXIT sim=$SIM_RC finalize=$FIN_RC" | tee -a "$LOG"
exit "$FIN_RC"
