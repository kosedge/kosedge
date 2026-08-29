# Defense SoT accept #306 — human list executed (2026-08-29)

**Branch:** `cursor/populate-defense-sot-7d1e` → `deploy-vercel`  
**Pack:** `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json`  
**Final pack sha256:** `0e4bb01348564dfec970ae244d16247accd51c4b291c6ba3376811a9194be45d`

## Disposition (marks followed — zero bulk-apply of printed EDGE1 patches)

| team | player | disposition | notes |
|------|--------|-------------|-------|
| MIN | Jamal Adams | **accepted** | S1 `injury_status=ir`, `confirmation=high` |
| NO | Bryan Bresee | **accepted** | DL1 IR (starter already implied by durable fact); `confirmation=high` |
| SEA | Bud Clark | **accepted** | S `depth_order=2` / `depth_slot=depth` IR — **NOT S1** |
| CAR | Nic Scourton | **accepted (IR-only)** | Edited patch: stripped EDGE1 seed → `depth_order=2` / `depth_slot=depth` + IR. **IR-only succeeded** (no EDGE1 crown) |
| CAR | Jaelan Phillips | **no_change** | Did **not** create healthy EDGE1 |
| GB | Micah Parsons | **no_change** | PUP stays PUP; no unit shock |

## Remat run ids + line_delta

| player | remat_run_id | line_delta |
|--------|--------------|------------|
| Adams | `9b9af368-77d3-4638-a96f-fbce2ed0d07d` | GB @MIN spread +0.55 / total +0.18 — `Jamal Adams S1 out — shock_table_v1 … (confirmation=high)` |
| Bresee | `ba57dfbf-1f54-4aab-b1f3-2f75d96c14df` | NO @DET spread −0.60 / total +0.20 — `Bryan Bresee DL1 ir … (confirmation=high)` |
| Clark | `e53a5b0d-4773-4d9a-9cb6-14959ddb86ad` | NE @SEA spread +0.35 / total +0.10 — `Bud Clark S2 ir … (confirmation=high)` |
| Scourton | `f71bd62b-f2ff-45e1-a407-2a2e6cdc9610` | CHI @CAR spread +0.35 / total +0.10 — `Nic Scourton EDGE2 ir … (confirmation=high)` |

CLI: `queue_camp_sot_flags.py --accept … --write --rematerialize` with `live_remat_fn` (Celery). Phillips/Parsons: `--no-change`.

## Scourton constraint

Printed populate patch had `create_if_missing` + `depth_order=1` / `starter`. Accept path **edited** proposed_patch to IR-only non-starter seed (`depth_order=2`, `depth_slot=depth`) so blank pack cannot crown EDGE1. Result: CAR EDGE2 IR row; Jaelan Phillips absent.

## STOP

No weather / ID-map / CFB. No further accepts in this pass.
