# NFL #564 remediation — 2026-09-15

**Track:** NFL only.  
**production_promote:** `false`  
**Boards:** Coming soon stays (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`).  
**Scoring equation:** unchanged (prior 45.3 / HFA 1.05 / efficiency caps ±5 total ±6.5 margin).  
**Recommendation:** **HOLD public.** Ryan CLEAR still required before any board reopen.

Investigation (#564 / `cf0324f1`) diagnosed the break. This package executes the authorized fix path only.

---

## Before / after readiness

| Metric | Before (#564 investigate, Railway 2026-09-15T18:01:54Z) | After this remediating path |
|---|---|---|
| Readiness HTTP | 503 | still 503 (min_sample_size=100 not met; **not a reopen**) |
| `sample_size` | **0** | **16** (W1 completed REG games) |
| `last_game_date` | `null` | **2026-09-14** (DEN@KC) |
| `coverage_source` | empty quality snapshot | `nfl_market_outcomes` when snapshot sample is 0 |
| `current_week` | **1** (date-window stuck on W1 Monday) | **2** once W1 rows are completed/ingested |

Fixture + merge proof: `data/ops/nfl-564-remediation-20260915/week1_outcomes_coverage.json`  
Live-before stamps remain: `data/ops/nfl-regression-live-stamps-20260915.json`.

Ingest change: `pull_nfl_outcomes` now fetches ESPN for **any** missing score / non-final `games.status` (the W1 foot-gun). It persists `nfl_market_outcomes`, stamps `nfl_dp_schedules` scores, and marks the game final. Readiness folds those outcomes in when the weekly quality snapshot is still empty.

---

## Packaged EPA authority

| Path | Before | After |
|---|---|---|
| Batch remat `run_nfl_market_simulations` | `_resolve_team_strength_indices` prefers EPA (`f6bcb284`) | **unchanged resolver**; new `prefer_packaged_epa=true` + `force_overlays_off=true` |
| Ad-hoc `POST /nfl/simulations/{id}` | Multiplied ESPN W-L context × injury and **INSERTed** | Calls `resolve_adhoc_simulation_strength` — **EPA or HTTP 409 refuse** |

Refuse code: `nfl_wl_persist_refused`. Tests: `tests/test_nfl_564_remediation.py` (`test_adhoc_uses_packaged_epa_not_win_loss`, `test_adhoc_refuses_when_packaged_epa_missing`, `test_adhoc_route_source_is_epa_or_refuse`).

`f6bcb284` is **not** rolled back.

---

## W2+ remat (overlays OFF)

Research remat only. No production write. No Coming soon flip.

| Field | Value |
|---|---|
| Run ID | `nfl-564-remediation-20260915-w2` |
| Strength | packaged EPA prior (`nfl_team_epa_priors_2026.json`) |
| Personnel overlay | **OFF** (margin 0 on all 16 W2 games) |
| Injury overlay | **OFF** (margin 0 on all 16 W2 games) |
| Game count | 16 |
| Checksum SHA256 | `11878ee10c52b541f9d48466d009728ef52d34963a3288d65359a2838ec833c9` |
| Artifact | `data/ops/nfl-564-remediation-20260915/w2_remat_epa_overlays_off.json` |

Worker remat (when a DB is available):

```bash
# Per slate date; overlays off; packaged EPA only
POST /api/jobs/run-nfl-simulations?game_date=2026-09-17&force_overlays_off=true&prefer_packaged_epa=true
POST /api/jobs/run-nfl-simulations?game_date=2026-09-20&force_overlays_off=true&prefer_packaged_epa=true
POST /api/jobs/run-nfl-simulations?game_date=2026-09-21&force_overlays_off=true&prefer_packaged_epa=true
```

Do **not** turn personnel/injury ON until the multi-matchup check below stays pass.

---

## Multi-matchup integrity

| Field | Value |
|---|---|
| Focus | DET@BUF, CAR@ATL, ATL@PIT, CHI@CAR |
| W-L vs EPA material (≥0.75 spread pts) | ATL@PIT, CHI@CAR (≥2 required) |
| Overlay leak | none |
| Double-count check | **pass** |
| Integrity checksum | `3ee913394af5a8a9c5fdee5d880f39b1c8541d8641938952772158b369ed0190` |
| Artifact | `data/ops/nfl-564-remediation-20260915/multi_matchup_integrity.json` |

CHI@CAR actual 96 vs EPA ~45 remains a **compressed-model residual**, not a license to edit the scoring equation.

---

## Reproduce

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/nfl_564_remediation_remat.py
PYTHONPATH=services/model-service python3 -m pytest \
  services/model-service/tests/test_nfl_564_remediation.py \
  services/model-service/tests/test_nfl_regression_decompose.py \
  services/model-service/tests/test_nfl_tasks.py::test_pull_nfl_outcomes_fetches_espn_when_status_is_not_final \
  -q
```

---

## Next gate (HOLD)

1. Run `pull_nfl_outcomes` + readiness on Railway; confirm live `sample_size=16` and `current_week=2`.
2. Optional DB remat of W2 dates with `force_overlays_off` + `prefer_packaged_epa` (shadow only).
3. Do **not** enable personnel/injury overlays yet.
4. Leave `NFL_EDGE_BOARD_PUBLIC_ENABLED=false`. No `production_promote`.
5. Ryan CLEAR still required before any board reopen.
