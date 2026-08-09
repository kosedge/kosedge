# Daily Roster + Injury Intel → SoT → Engine

Cadence: **daily in camp / in-season**; more often on flash injury days.

Authoritative pack:  
`services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json`

Engine rule: when the pack exists, it is the **only** player→team + skill depth SoT. No dual maps. No one-off simulator hardcodes.

## Checklist

### 1. Ingest
- [ ] Pull current skill depth + injury intel (team IR/PUP, official reports, beat notes, RotoWire).
- [ ] Prefer primary sources over rumor.
- [ ] Note flashpoints with **citations** and run-time verify date (`YYYY-MM-DD`).

### 2. Diff vs SoT
- [ ] Team changes (FA / trade / cut).
- [ ] Starter job changes (depth_order / depth_slot).
- [ ] OUT / limited / returning (+ window when known; else `unknown / monitor`).
- [ ] OL starter slides (track in `ol_roles` — not skill usage rows).

### 3. Write SoT only
- [ ] Edit the depth pack (or re-run packager + re-apply SoT overlays).
- [ ] Skill rows: QB/RB/WR/TE depth 1–3 + **required** `player_id` (GSIS) + optional `injury_*`.
- [ ] `ol_roles`: LT/LG/C/RG/RT starter vs backup vs out.
- [ ] `injury_paths[]`: **only** when week windows are known — do not invent IR lengths.
- [ ] `camp_intel` + `ol_efficiency_hooks`: document OL→EPA pathway honestly (`documented_not_magical` until calibrated).
- [ ] Bump `as_of` / `daily_intel_as_of` / `snapshot_id` (effective-dated).
- [ ] Keep packager `SOT_QB_OVERRIDES` / `SOT_SKILL_OVERRIDES` in sync so re-packaging cannot wipe camp SoT.

### 4. Integrity gate (hard-fail — required before re-sim)
- [ ] Archive + validate:

```bash
bash scripts/nfl/run_daily_roster_injury_intel.sh --gate
# or: python scripts/nfl/run_data_integrity_gate.py --archive --require-archive
```

- [ ] Gate must **PASS** (duplicates, missing QB1, share blow-up, stale, role gaps, engine↔web sample).
- [ ] Record `snapshot_id`, pass/fail, teams touched in the ops note.
- [ ] **Do not re-sim downstream until PASS.** Phase 2 blocked while red.

### 5. Propagate
- [ ] Confirm loader path is pack-primary (`build_packaged_real_universe` / DB loader ignores weekly when pack present).
- [ ] Re-sim affected teams (or full board on flash days):

```bash
bash scripts/nfl/run_daily_roster_injury_intel.sh --sim
```

- [ ] Conservation: pass/rush pools OK; **Σ mean wins = 272**.
- [ ] Confirm `run_summary.json` / survivor outputs carry `lineage.snapshot_id`.

### 6. Report
- [ ] Before/after high-impact roles (starters, OUT, slides).
- [ ] Teams whose PF / wins moved.
- [ ] KEI attention notes (esp. OL stacks where `injury_at_time_depth` is still stub).
- [ ] Write `data/ops/nfl-daily-roster-intel-YYYYMMDD.md` with gate results.

### 7. Ship
- [ ] Branch off `deploy-vercel`.
- [ ] Tests: `pytest services/model-service/tests/test_nfl_data_integrity_gate.py tests/test_nfl_roster_source_of_truth.py -q`
- [ ] PR → `deploy-vercel`.

## Do not
- Patch a single player inside the simulator.
- Leave packaged depth as silent fallback when SoT exists (pack is exclusive).
- Touch locked pass-pool / alpha / coherence except via corrected depth → budgets → allocation.
- Invent injury lengths.

## Quick verify

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json')
d = json.loads(p.read_text())
print('as_of', d.get('as_of'), 'daily_intel', d.get('daily_intel_as_of'))
print('injury_paths', len(d.get('injury_paths') or []))
print('ol_roles', len(d.get('ol_roles') or []))
PY
```
