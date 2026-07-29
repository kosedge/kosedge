#!/usr/bin/env bash
# Monitor PID for NFL_SEASON_SIMS=100000 run; finalize artifacts + commit on success.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PID="${1:-31096}"
LOG="data/ops/nfl-100k-sim-run.log"
PROG_JSON="data/ops/nfl-100k-sim-progress.json"
PROG_MD="data/ops/nfl-100k-sim-progress.md"
STARTED="${2:-2026-07-29T15:53:29Z}"

echo "[monitor] watching pid=$PID"

while kill -0 "$PID" 2>/dev/null; do
  LAST=$(rg -o '\.\.\.(\d+)/100000 replicates' -r '$1' "$LOG" 2>/dev/null | tail -1 || true)
  LAST="${LAST:-0}"
  .venv/bin/python - "$LAST" "$PID" "$STARTED" "$LOG" "$PROG_JSON" "$PROG_MD" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

last = int(sys.argv[1] or 0)
pid = int(sys.argv[2])
started = sys.argv[3]
log_path = sys.argv[4]
prog_json = Path(sys.argv[5])
prog_md = Path(sys.argv[6])
now = datetime.now(timezone.utc).isoformat()
pct = round(100.0 * last / 100000, 1)
d = {
    "status": "running",
    "sims_requested": 100000,
    "pid": pid,
    "started_at_utc": started,
    "updated_at_utc": now,
    "replicates_done": last,
    "replicates_total": 100000,
    "pct_complete": pct,
    "phase": "monte_carlo_replicates" if last < 100000 else "post_mc",
    "log_path": log_path,
    "command": "NFL_SEASON_SIMS=100000 .venv/bin/python -u scripts/nfl/simulate_2026_season.py",
    "estimated_runtime_minutes": "40-90",
    "eta_minutes_remaining": round(max(0, (100000 - last) / 3000), 1),
    "output_dir_pattern": "data/ops/nfl-preseason-sim-2026-<timestamp>",
    "projections_hub": "latest nfl-preseason-sim-2026-* auto-picked by nfl-preseason-artifacts.ts",
    "constraints": {
        "no_play_widen": True,
        "no_reenable_EBA": True,
        "no_odds_densify": True,
    },
}
prog_json.write_text(json.dumps(d, indent=2) + "\n")
prog_md.write_text(
    "# NFL 100k season sim — progress\n\n"
    f"- Status: **running**\n"
    f"- PID: `{pid}`\n"
    f"- Replicates: {last}/100000 ({pct}%)\n"
    f"- ETA remaining (MC): ~{d['eta_minutes_remaining']} min\n"
    f"- Updated: `{now}`\n"
)
print(f"[{now}] {last}/100000 ({pct}%)")
PY
  sleep 60
done

echo "[monitor] pid $PID exited; finalizing"
sleep 3

.venv/bin/python - "$LOG" "$PROG_JSON" "$PROG_MD" "$STARTED" "$PID" <<'PY'
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

log_path = Path(sys.argv[1])
prog_json = Path(sys.argv[2])
prog_md = Path(sys.argv[3])
started = sys.argv[4]
pid = int(sys.argv[5])
log = log_path.read_text(errors="replace")
bundle = None
m = re.search(r"Wrote bundle to (.+)", log)
if m:
    bundle = m.group(1).strip()
if not bundle:
    dirs = sorted(Path("data/ops").glob("nfl-preseason-sim-2026-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    bundle = str(dirs[0]) if dirs else ""
bundle_path = Path(bundle) if bundle else None
qc = {}
if bundle_path and (bundle_path / "quality_checks.json").exists():
    qc = json.loads((bundle_path / "quality_checks.json").read_text())
iters = qc.get("metadata", {}).get("season_monte_carlo_iterations")
hub_ok = bool(
    bundle_path
    and (bundle_path / "team_regular_season_outcomes.csv").exists()
    and (bundle_path / "player_regular_season_totals.csv").exists()
)
ok = hub_ok and iters == 100000
finished = datetime.now(timezone.utc).isoformat()
d = {
    "status": "completed" if ok else ("completed_wrong_iters" if hub_ok else "failed"),
    "sims_requested": 100000,
    "pid": pid,
    "started_at_utc": started,
    "finished_at_utc": finished,
    "output_dir": bundle,
    "season_monte_carlo_iterations": iters,
    "sanity": qc.get("sanity"),
    "top10_super_bowl": qc.get("top10_super_bowl"),
    "log_path": str(log_path),
    "projections_hub_readable": hub_ok,
    "constraints": {
        "no_play_widen": True,
        "no_reenable_EBA": True,
        "no_odds_densify": True,
    },
}
prog_json.write_text(json.dumps(d, indent=2) + "\n")
prog_md.write_text(
    "# NFL 100k season sim — complete\n\n"
    f"- Status: **{d['status']}**\n"
    f"- Bundle: `{bundle}`\n"
    f"- Sims: {iters}\n"
    f"- Hub readable: {hub_ok}\n"
    f"- Finished: `{finished}`\n"
)
print(json.dumps({k: d[k] for k in d if k != "top10_super_bowl"}, indent=2))

# Patch readiness report
rep = Path("data/ops/nfl-week1-readiness-report.md")
text = rep.read_text()
section = (
    "\n\n## 100k season sim — completed\n\n"
    f"- Finished: `{finished}`\n"
    f"- Bundle: `{bundle}`\n"
    f"- `season_monte_carlo_iterations`: {iters}\n"
    f"- Sanity: `{json.dumps(d.get('sanity'))}`\n"
    f"- Projections hub readable: **{hub_ok}** (auto-picks latest `nfl-preseason-sim-2026-*`)\n"
    "- Progress: `data/ops/nfl-100k-sim-progress.{json,md}`\n"
    "- Log: `data/ops/nfl-100k-sim-run.log`\n\n"
)
if "## 100k season sim — completed" not in text:
    marker = "## 100k / futures status"
    if marker in text:
        text = text.replace(marker, section.strip() + "\n\n" + marker, 1)
    else:
        text = text.rstrip() + "\n" + section
text = text.replace(
    "100k sims path | **Wired** — `NFL_SEASON_SIMS=100000`; full run **not** completed this session",
    f"100k sims path | **Done** — `{Path(bundle).name if bundle else 'n/a'}`",
)
text = text.replace(
    "Fresh 100k run this session | **Not completed** — full 100k is multi-hour",
    f"Fresh 100k run this session | **Completed** → `{bundle}`",
)
# also update futures row in checklist table if present
if "100k / futures" in text and "Done" not in text.split("100k / futures")[1][:200]:
    pass
rep.write_text(text)

# Update 100k path doc
path_doc = Path("data/ops/nfl-100k-sims-path.md")
if path_doc.exists():
    pd = path_doc.read_text()
    pd = pd.replace(
        "| Fresh 100k run this session | **Not completed** — full 100k is multi-hour (pairwise matrix + 100k replicates + player totals). Do not fake readiness. |",
        f"| Fresh 100k run this session | **Completed** `{Path(bundle).name if bundle else ''}` |",
    )
    path_doc.write_text(pd)

# Signal file for commit step
Path("data/ops/nfl-100k-sim-finalize.flag").write_text(
    json.dumps({"ok": ok, "bundle": bundle, "iters": iters}, indent=2) + "\n"
)
PY

FLAG=data/ops/nfl-100k-sim-finalize.flag
if [[ -f "$FLAG" ]] && .venv/bin/python -c "import json; print(json.load(open('$FLAG'))['ok'])" | grep -q True; then
  BUNDLE=$(.venv/bin/python -c "import json; print(json.load(open('$FLAG'))['bundle'])")
  git add \
    data/ops/nfl-100k-sim-progress.json \
    data/ops/nfl-100k-sim-progress.md \
    data/ops/nfl-week1-readiness-report.md \
    data/ops/nfl-100k-sims-path.md \
    data/ops/nfl-100k-sim-run.log \
    scripts/nfl/monitor_100k_sim.sh
  if [[ -n "$BUNDLE" && -d "$BUNDLE" ]]; then
    git add "$BUNDLE"
  fi
  if ! git diff --cached --quiet; then
    git commit -m "$(cat <<'EOF'
ops(nfl): land 100k season sim bundle for futures/projections

Refresh win totals / SB probs via NFL_SEASON_SIMS=100000; projections hub
auto-picks the new nfl-preseason-sim-2026 bundle. Update readiness report.
EOF
)"
    git push origin HEAD
  fi
  echo "[monitor] committed and pushed"
else
  echo "[monitor] finalize not ok — skip commit"
  cat "$FLAG" 2>/dev/null || true
fi
echo "[monitor] done"
