# NFL Automation Phase 1 — 2026-08-13

Operate loop only. **Not a new model.** Preseason research pin stays until the first successful ROS checkpoint replaces it on purpose.

| Pin | Value |
|-----|--------|
| Lock tag | `nfl-season-engine-2026-preseason-lock` |
| Bundle | `nfl-preseason-sim-2026-20260813T214500Z` |
| Pointer | `data/ops/nfl-web-launch-bundle.json` (`locked_snapshot: true`) |
| Weekly props | gated (`NFL_WEEKLY_PROPS_LIVE = false`) |
| Vercel production | `deploy-vercel` |

Walker = KC RB1 · Charbonnet = SEA RB1 · Evans = SF · Egbuka = TB. Checksum QBs: Tua ATL / Willis MIA / Kyler MIN / ARI ≠ Kyler.

---

## How to run

### Weekly operate

```bash
# Preseason / rehearsal (PASS; does not flip the research pin)
python3 scripts/nfl/run_weekly_operate.py --dry-run

# After a finished REG week
python3 scripts/nfl/run_weekly_operate.py --week 5 --dry-run
python3 scripts/nfl/run_weekly_operate.py --week 5

# Optional skips
python3 scripts/nfl/run_weekly_operate.py --week 5 --skip-kei --skip-audit
```

Writes `data/ops/nfl-weekly-operate-last.json`. Weekly **never** writes `data/ops/nfl-web-launch-bundle.json`. Weekly **never** calls the ROS checkpoint (it only sets `ros_checkpoint_due` when `--week` is 4/8/12/16).

### ROS checkpoint

Checkpoints: **4, 8, 12, 16** (+ optional `--post-deadline` → week 9).

Default N_team = **50000**. 100000 is allowed on the plan via `--n-team-sims 100000`; actually running 100k requires `--execute --allow-100k`.

```bash
# Default: dry-run plan, no sim, no pointer flip
python3 scripts/nfl/run_ros_checkpoint_sim.py --after-week 4
python3 scripts/nfl/run_ros_checkpoint_sim.py --after-week 4 --dry-run

# Post–trade deadline (week 9)
python3 scripts/nfl/run_ros_checkpoint_sim.py --after-week 9 --post-deadline --dry-run

# Real re-sim + publish (pointer flips only if release gate PASS)
python3 scripts/nfl/run_ros_checkpoint_sim.py --after-week 4 --execute
python3 scripts/nfl/run_ros_checkpoint_sim.py --after-week 4 --execute --n-team-sims 100000 --allow-100k
```

`--execute` runs `scripts/nfl/run_launch_research_sims.py` then `scripts/nfl/publish_launch_research_to_web.py --lock-tag nfl-season-engine-2026-ros-w{N} --require-release-gate --apply-feature-floors`. Gate FAIL → pointer unchanged + `data/ops/nfl-ros-checkpoint-w{N}-failed.md`.

Does not change the Model vs KEI contract.

---

## Auto vs human_required today

| Stage | Auto now? | Notes |
|-------|-----------|--------|
| Results ingest | Auto **when** REG week ≥ 1 and pointer is no longer preseason | Hooks `run-weekly-inseason-update.sh` + `write_projection_actuals.py`. **Skip** in preseason (no fake games). |
| Proof log | Path check auto | Projection→close→result writer + proof lake module must exist. **Never wipes** the lake. Preseason does not write actuals. |
| Depth / injury | **human_required** | No live injury scrape. Drop approved JSON in `data/ops/nfl-daily-intel/pending/` then `apply_daily_intel_overrides.py --write`. Weekly job will not auto-write the SoT pack (Walker stays KC unless human override). |
| Identity audit | Auto | `audit_nfl_pack_vs_market.audit()`. **FAIL** if `CLEAR_ERROR > 0`. |
| KEI / board | Auto (read-time) | `check_edge_board_week1` + injury→KEI `--dry-run` heartbeat. No model version bump. Fair-lines read current KEI. |
| Health smoke | Auto (local) | Pointer lock + optional `GET $MODEL_SERVICE_URL/health`. Does **not** call `/health/nfl-production-readiness` (false degraded in preseason). Residual `injuries` honesty is not board degradation. |
| ROS re-sim | **human** `--execute` | Dry-run is the default. Weekly never starts it. |

---

## Cron: documented-only (not live)

One path: GitHub Action `.github/workflows/nfl-weekly-operate.yml`.

- **Today:** `workflow_dispatch` only. Schedule is commented. Enable the cron when Season Week ≥ 1.
- Not Railway cron. Not launchd. Do not enable three schedulers.

```yaml
# Enable when Season Week ≥ 1 (Tuesday after MNF, 12:30 UTC):
# schedule:
#   - cron: "30 12 * * 2"
```

Dispatch:

```bash
gh workflow run nfl-weekly-operate.yml -f week=0 -f dry_run=true
```

---

## Lock pin

Weekly path **cannot** flip the research pin. Confirm after any weekly run:

```bash
python3 -c "import json; p=json.load(open('data/ops/nfl-web-launch-bundle.json')); print(p['lock_tag'], p['locked_snapshot'])"
```

Must remain `nfl-season-engine-2026-preseason-lock` `True` until a ROS checkpoint `--execute` passes the release gate.

Release gate: `scripts/nfl/preseason_release_gate.py` — pointer cannot flip on red. Pack vs market: `scripts/nfl/audit_nfl_pack_vs_market.py` — weekly fails if `CLEAR_ERROR > 0`. `SOT_SKILL_OVERRIDES` in `package_season_engine_depth_2026.py` — Walker stays KC unless human override.

---

## Human-only list

- CLEAR_ERROR pack overrides (review mismatch markdown; no auto-move)
- Tag policy judgment
- True outages (Railway / Vercel / DB)
- Approved SoT intel writes
- ROS `--execute` (and any 100k)

---

## Last-run JSON schema

### `data/ops/nfl-weekly-operate-last.json`

```json
{
  "schema": "nfl-weekly-operate-last/v1",
  "generated_at_utc": "2026-08-13T22:00:00Z",
  "season": 2026,
  "week": 0,
  "dry_run": true,
  "status": "pass",
  "stages": [
    {
      "id": "results_ingest",
      "status": "skip",
      "detail": "…",
      "hook": "scripts/nfl/run-weekly-inseason-update.sh"
    }
  ],
  "human_required": ["depth_injury_hook: …"],
  "pointer_path": "data/ops/nfl-web-launch-bundle.json",
  "pointer_lock_tag": "nfl-season-engine-2026-preseason-lock",
  "pointer_flipped": false,
  "never_flips_research_pin": true,
  "weekly_props_live": false,
  "ros_checkpoint_due": false,
  "ros_checkpoint_note": "weekly path never calls ROS checkpoint",
  "preseason_lock_tag": "nfl-season-engine-2026-preseason-lock",
  "stage_order": [
    "results_ingest",
    "proof_log",
    "depth_injury_hook",
    "identity_audit",
    "kei_board_rebuild",
    "health_smoke"
  ]
}
```

Stage `status` ∈ `pass` | `fail` | `skip` | `human_required`. Top-level `status` is `fail` if any stage fails, else `pass` (skip / human_required do not fail the job).

### `data/ops/nfl-ros-checkpoint-last.json`

```json
{
  "schema": "nfl-ros-checkpoint-last/v1",
  "generated_at_utc": "2026-08-13T22:00:00Z",
  "after_week": 4,
  "dry_run": true,
  "execute": false,
  "n_team_sims": 50000,
  "n_player_sims": 1000,
  "lock_tag": "nfl-season-engine-2026-ros-w4",
  "plan": { "sim": "…", "gate": "…", "publish": "…" },
  "pointer_flipped": false,
  "pointer_lock_tag_before": "nfl-season-engine-2026-preseason-lock",
  "status": "pass",
  "require_release_gate": true,
  "model_vs_kei": "unchanged"
}
```

---

## Explicit non-goals (this phase)

- New EPA / volume / coherence rewrite
- Auto-ungating weekly player props
- Full live injury scrape
- CFB automation
- Mobile app
- Efficiency backbone / continuity formula edits
