# NFL projected / fair regression — investigation (2026-09-15)

**Track:** NFL only. Separate from CFB NAME_TO_CODE / residual work.  
**production_promote:** `false`  
**Boards:** Coming soon stays (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`, PR #561 / `8dd128ce`).  
**This PR:** diagnosis + reproducible decompose + regression tests. **No scoring-equation edit. No rematerialize. No board reopen.**

Railway / www evidence captured **2026-09-15T18:01:54Z**.  
Payload checksums + SHAs: `data/ops/nfl-regression-live-stamps-20260915.json`.

---

## 1) Last reasonable vs first abnormal

| Anchor | When | Code / run | What it looked like |
|---|---|---|---|
| **Last reasonable customer paint** | 2026-09-08 ~16:11Z | Same KEI stamps as today; documented in `docs/incidents/INC-2026-09-08-NFL-EDGE-BOARD-CUSTOMER-TRUTH/` | ARI@LAC KEI −8.31 vs mkt **−9.5**; BAL@IND +1.76 vs **+3.5**; NYJ@TEN −2.97 vs **−1.5**. Display contract was wrong; **research fairs were stable and market-joined.** |
| **Last reasonable research freeze** | 2026-07-31T06:05Z | Worker canary `props-under-bias-20260731c-baselines-box-rebuild`; model `nfl-v1.5-matchup-sim`; **`active_run_id = null`** | All 48 W1–W3 fair-line rows still carry this `projection_created_at`. EPA-prefer resolve already in tree (`f6bcb284`, 2026-07-19). Totals prior **45.3** already in tree (`4f348b28`, 2026-07-21). |
| **First abnormal pipeline** | Week 1 window (2026-09-10 → 09-15) | `pull_nfl_context_snapshot` + **empty outcomes** | `/health/nfl-production-readiness` → **503**, `sample_size=0`, `last_game_date=null`. `/nfl/games` now shows **1-0 → 1.12/1.12**, **0-1 → 0.90/0.92** (ESPN W-L). `current_week` still **1**. Week-1 KEI reprice **applied_games=0** on the W2/W3 board. |
| **First abnormal vs actuals** | Week 1 finals | ESPN scoreboard 2026-09-10/13/14 | Model totals stayed **40–46**. Actuals: CHI@CAR **96**, BAL@IND **64**, BUF@HOU **67**, SF@LAR **34**, ATL@PIT **33**. |
| **First abnormal market join (completed games)** | After kickoff | Live Odds attach on `include_past_days` | SF@LAR mkt **+15.5**, BAL@IND **+17.5**, NYJ@TEN **+13.5**, CHI@CAR **+14.5**, BUF@HOU total **63.5**. Contrast Sept 8 sane markets on the same KEI stamps. |

www `GET /api/nfl/fair-lines` is **503** `nfl_edge_board_unavailable` (Coming soon). Model-service still serves the July-31 rows. That is fail-closed display, not a remat.

### Preserved identities

| Item | Value |
|---|---|
| Investigation HEAD / Railway `git_sha` | `60ec705104783508d0326990373aadcb280dc684` |
| Coming soon flip | `8dd128ce` (#561) — **leave false** |
| EPA-over-record resolve | `f6bcb284` |
| Totals prior 45.3 | `4f348b28` |
| Packaged EPA priors | `nfl_team_epa_priors_2026.json` as_of **2026-08-08** |
| Live W2/W3 fair-lines SHA256 | `2d7bf46187b001fc62566cc68fba35c3f551ec34d8668cd72a1a0f7bcaf69f6b` |
| Live W1 fair-lines SHA256 | `be0cb5f7f46113bec4fa16c921826884415e2f7980e0d2423f764e5b40a80fab` |
| Lineage | `run_id=nfl-v1.5-matchup-sim`, `active_run_id=null` |

---

## 2) Same matchups, two strength books

Replay (no market blend, no injury, no personnel) via:

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/nfl_projected_points_decompose.py
```

| Game | Live Model (Jul 31) | EPA prior only (2025 pack) | W-L bucket after W1 | Notes |
|---|---:|---:|---:|---|
| DET@BUF W2 | −3.83 / 44.46 | −1.58 / 46.10 | both 1-0 → −1.05 / 45.30 | Live extra ~2 pts is matchup/blend, **not** W-L. Market total 53.5. |
| CAR@ATL W2 | **−2.77** / 43.70 | **−2.90** / 44.53 | both 0-1 → **−1.05** / 44.84 | July-31 model **tracks EPA**, not record. Market now ATL **+2.5** (favorite flip vs KEI). |
| ATL@PIT W1 | −2.75 / 43.49 | −0.76 / 44.65 | 0-1 @ 1-0 → **−7.55** / 45.52 | Actual **13–20** (total 33). W-L remat would **over-move** PIT. |
| CHI@CAR W1 | +0.72 / 44.29 | +1.27 / 45.50 | 1-0 @ 0-1 → **+5.45** / 45.52 | Actual **59–37** (total **96**). Equation band cannot reach 96. |

W-L vs EPA spread delta is **≥ 0.75 pts on ATL@PIT and CHI@CAR** (and more). The failure is not a one-game special case.

---

## 3) Projected points — components

`compute_nfl_projection_decomposition` (framework `nfl-handicap-core-v3.1`):

```
predicted_margin = Σ factor.margin_points
predicted_total  = 45.3 + Σ factor.total_points     # clamp 30–66
home_pts         = max(7.5, (total + margin) / 2)
away_pts         = max(7.0, (total − margin) / 2)
```

On the investigation replay (injury / personnel / KAV / DVOA off — same as `season_too_early`):

| Component | Margin | Total | Status on this probe |
|---|---:|---:|---|
| `base_efficiency` | off/def ratio × 16, clamp ±6.5 | ratio × 10.5, clamp ±5.0 | **Only material research term** |
| `home_field_advantage` | +1.05 | 0 | Static |
| `injuries_depth` | 0 | 0 | Zeroed: outcomes missing → `completed_reg < 3` → `season_too_early` |
| `personnel_efficiency` | 0 | 0 | Same gate. **Historical double-count risk if remat turns this on on top of current-season EPA.** |
| rest / weather / travel / regression | 0 | 0 | No extra signals in this probe |

Live KEI ≠ Model because **market blend + totals calibration** still run on the July-31 sim (`model_equals_kei=false` on all 32 upcoming rows). That is why W2 KEI can look “close” to the street (spread MAE ~1.4) while research totals sit ~44.

---

## 4) Root-cause classification

More than one bucket. **Not** “the scoring equation broke last week.”

1. **Data / stale inputs — PRIMARY**  
   Every fair-line projection is still **2026-07-31**. Outcomes job has not landed Week 1 (`sample_size=0`). No remat, no `active_run_id`, `current_week` stuck at 1. Week-1 KEI desk reprice does not apply to W2/W3 (`not Week 1 REG 2026 — reprice skipped`).

2. **Roster / QB / injury / HFA — SECONDARY**  
   `season_too_early = completed_reg_season < 3` (`tasks.py`). With **zero ingested finals**, injury / QB / tendency overlays stay neutralized even after real Week 1 games. HFA 1.05 is the only always-on add-on.

3. **Units / defaults / silent W-L — CONTRIBUTING (foot-gun)**  
   `pull_nfl_context_snapshot` still writes `team_strength_from_record` (0.90+0.22·win%, 0.92+0.20·win%) into `nfl_game_context`. Live `/nfl/games` is already the two-bucket board.  
   Batch remat **prefers EPA** (`_resolve_team_strength_indices`, `f6bcb284`).  
   **`POST /nfl/simulations/{game_id}` does not.** It multiplies those W-L indices by injury nowcast and **INSERTs** a new `nfl_market_projections` row. Sentinel: `NFL_REGRESSION_20260915` in `src/routes/nfl.py`.

4. **Double-counting personnel on team strength — WATCH, not proven on the freeze**  
   Personnel is a separate factor on top of `base_efficiency`. July-31 + `season_too_early` keeps it at 0. A naive remat after outcomes land could add personnel **and** current-season EPA. Do not turn both on as a “fix.”

5. **Scoring equation itself — NOT the break**  
   Prior 45.3 / HFA 1.05 / efficiency caps ±5 total ±6.5 margin are unchanged since **2026-07-21**. Tests lock `LOCKED_SCORING`. CHI@CAR 96 vs ~44 is a **compressed-model residual**, not a new formula defect. Do not raise the prior to chase Week 1.

6. **Correct model, wrong display — CONFIRMED for completed-game markets only**  
   Sept 8 vs today on the **same** KEI: market fields on past games are unusable. Upcoming W2/W3 joins look like real NFL numbers (DET@BUF −4.5 / 53.5). Customer boards are already Coming soon.

---

## 5) Rollback candidate (verified, then rejected)

| Candidate | Still sane? | Verdict |
|---|---|---|
| Roll **code** to pre-`f6bcb284` (prefer W-L) | No. Audit already showed W-L MAE **worse than the market** (10.73 vs 9.79) on 855 games. After Week 1 it would paint PIT −7.6 vs EPA −0.8. | **Do not rollback.** |
| Treat July-31 stamps as the “good” research book | Sane **vs Sept 8 market**. Not sane **vs Week 1 actuals** (ARI +7.08 underdog won 26–14; several 60+ totals). | **Keep as frozen SoT until remat is safe. Do not promote as a fix.** |
| Re-open boards / flip Coming soon | www already 503. Model-service still serves stale rows. | **Keep dark.** |

---

## 6) Proposed next action (not this PR)

**Deeper probe, then a fail-closed remat — not a scoring retune.**

1. Ingest Week 1 outcomes (`pull_nfl_outcomes`) until readiness `sample_size` covers the 16 games and `last_game_date` is 2026-09-14. Re-run decompose vs actuals.  
2. Confirm `_count_completed_reg_games_season` moves off 0 **before** any remat (this is what lifts `season_too_early`).  
3. Wire `_resolve_team_strength_indices` into `POST /nfl/simulations/{id}` **or** refuse persist when context looks like the W-L two-bucket. Update `test_adhoc_simulation_route_still_bypasses_epa_resolve`.  
4. Remat W2+ on EPA priors only, injury overlays labeled, personnel **off** until a double-count check passes on ≥2 games (DET@BUF and CAR@ATL plus ATL@PIT / CHI@CAR).  
5. Re-check residuals on **more than one** matchup before any `production_promote` discussion.  
6. Leave `NFL_EDGE_BOARD_PUBLIC_ENABLED = false`. No CFB work in the remat PR.

---

## 7) Reproducible commands

```bash
# Live (read-only)
curl -sS https://www.kosedge.com/api/nfl/fair-lines?season=2026
# → 503 nfl_edge_board_unavailable

curl -sS https://model-service-production-e253.up.railway.app/health
# git_sha 60ec70510478

curl -sS "https://model-service-production-e253.up.railway.app/nfl/fair-lines?season=2026" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['count'], {x.get('projection_created_at','')[:10] for x in d['lines']})"

curl -sS "https://model-service-production-e253.up.railway.app/nfl/fair-lines?season=2026&include_past_days=14&days_ahead=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['count'], d['current_week'])"

curl -sS https://model-service-production-e253.up.railway.app/health/nfl-production-readiness
# 503 sample_size=0

# Local decompose (no Railway writes)
PYTHONPATH=services/model-service python3 scripts/nfl/nfl_projected_points_decompose.py
PYTHONPATH=services/model-service python3 -m pytest \
  services/model-service/tests/test_nfl_regression_decompose.py -q
```

Coming soon / CFB kill switch files are **not** modified in this PR.
