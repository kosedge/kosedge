# NFL spine LIVE smoke — 2026-08-20

**Status:** Part A not fully green → **`NFL_WEEKLY_PROPS_LIVE = false` (no-go)**  
**Branch from:** `deploy-vercel` @ `#269` (`8d201b50`)  
**Spine version:** `player-production-v3-phase3c`  
**Edge cal:** unchanged `prop-structure-cal-v1` (edge math only)  
**Checked:** 2026-08-20 14:38–14:47 UTC against Railway `production` / public Postgres

No PLAY / blend / DK-FD / structure-knob changes in this note.

---

## Smoke table (A)

| Gate | Result | Evidence |
|------|--------|----------|
| A1 services | **RED** | API / worker / beat / Postgres **Online**, but worker is **not draining**. Celery `models` LLEN **1478**, `default` **9**, `odds` **43**. Default still holds **4× `run_nfl_props_layer_rebuild` + 5× `materialize_nfl_player_baseline_projections`** (bare kwargs — same week-22-only class as the #268 incident). No Redis `unacked`/`active`. Worker logs stop ~03:23 UTC after 2023/2024 remats. Beat still enqueueing (MLB nowcast dominates the backlog). |
| A2 prod parity | **GREEN** | Features + baselines present 2023–25. 2025 cap-17 pool: **max 4590 / n=4 / gap 0.097** (matches 3C expect). |
| A3 equality | **GREEN** | 2025 w1 DB rows: n=40 all equal; mixed 8 QB / 8 RB / 8 WR also 24/24. Spine `player-production-v3-phase3c`. |
| A4 surfaces | **YELLOW** | Fantasy desk **200** (Gibbs #1; McCaffrey/Prescott present). Props **200** with honest gate. No false “degraded” banner. Season path is **not** live SUM spine: `nfl_fantasy_season_draft_rankings` is **empty**; desk serves **preseason-bundle fallback**. Weekly fantasy API 500. No 2026 box sims. |

**Gate:** Part B is **no-go**. LIVE stays false. Fix infra + 2026 SUM path before any flag flip.

---

## A1 — Railway services

| Service | Railway | Probe |
|---------|---------|-------|
| model-service / API | Online · deployed 2026-08-19 23:07 ET (`#269`) | `/health` ok · `/health/db` connected · `/health/celery` ok |
| model-service-worker | Online · same deploy | Celery ready 03:07 UTC; processed remats; **not consuming since ~03:23 UTC** |
| model-service-beat | Online · same deploy | Scheduling through 14:40 UTC (odds, props hourly, NFL sims, MLB nowcast) |
| Postgres | Online | Direct query ok |

`/health/nfl-data-freshness`: product `status=ok`, `in_season=false`. Only enforced ops blocker is **stale DR backup** (`255.7h > 192h`). Web maps `dr_backup:` as ops-only — not a guest “boards degraded” banner.

`/health/nfl-production-readiness`: `no-go` (sample_size 0, Aug 13 snapshot). That is the **game-board quality gate**, not the weekly-props spine gate. Do not treat it as a props LIVE signal.

### Worker / rematerialize timeline (post `#269`)

| UTC | Event |
|-----|--------|
| 03:06 | `#269` merged |
| 03:07 | Worker `celery@fe5aa060b5a7 ready` |
| 03:07 | `run_nfl_props_layer_rebuild` **2025 weeks=[22]** and **2024 weeks=[22]** succeeded in ~2s (bare `season=` path) |
| 03:15 | Full **2023 w1–18** remat succeeded (~457s; feature_rows 5381) |
| 03:23 | Full **2024 w1–18** remat succeeded (~461s; feature_rows 5313) |
| after | **No further worker success logs.** Beat kept enqueueing. Queues grew. |

No `IndexError` / `parents[5]` / path-as-root crash in the current worker boot. The `#268` class crash did **not** recur. The residual risk is **hung/non-consuming worker + leftover bare rematerialize on `default`**.

**Do not restart the worker** while those 4 bare `run_nfl_props_layer_rebuild` jobs sit on `default` — they can week-22-only “succeed” again. Revoke/purge those remats first, then drain or bounce.

---

## A2 — Prod data parity

### Features / baselines

| Season | Features | Feature weeks | Baselines | Baseline weeks | Latest baseline `updated_at` (UTC) |
|--------|----------|---------------|-----------|----------------|-------------------------------------|
| 2023 | 5628 | 1–22 | 5402 | 1–18 + 22 | 2026-08-20 03:14 |
| 2024 | 5568 | 1–22 | 5333 | 1–18 + 22 | 2026-08-20 03:22 |
| 2025 | 5612 | 1–22 | 5612 | 1–22 | 2026-08-20 03:07 (week 22 only) |
| 2026 | — | — | 52326 | 1–18 (2907/week) | 2026-07-19 |

2023–25 coverage is the served historical spine. 2026 is a **different grain** (densified / pre-3C), not the 3C rematerialize.

### 2025 cap-17 pool (prod, `nfl-player-v1`)

| Metric | 3C expect | **Prod now** |
|--------|-----------|--------------|
| Max QB pass | ~4590 | **4590** (D.Prescott DAL, 17g) |
| n ≥4000 | 4 | **4** (Prescott 4590, Goff 4379, Stafford 4277, Williams 4054) |
| Pass↔rec gap | ~0.097 | **0.097** |

Next QBs sit under the line (Lawrence 3998, Mayfield 3992).

### 2026 cap-17 (not a LIVE input)

| Metric | Value |
|--------|-------|
| Max QB pass | 4123 (Goff) |
| n ≥4000 | 3 |
| Pass↔rec gap | **0.299** |

2026 is not 3C-coupled. Do not promote weekly props off this table.

---

## A3 — Equality smoke

Helper: `production_from_baseline_row` on **prod** `nfl_player_projection_baselines` (not synthetic).

| Sample | n | equal | mismatch | source |
|--------|---|-------|----------|--------|
| 2025 w1 first 40 (pos/team/name) | 40 | 40 | 0 | database |
| 2025 w1 mixed 8/8/8 QB/RB/WR | 24 | 24 | 0 | database |

**Spine version:** `player-production-v3-phase3c`

Artifacts: `nfl-spine-live-smoke-equality-20260820.json`, `nfl-spine-live-smoke-equality-mixed-20260820.json`.

Mixed excerpt (means from weekly spine; props path == fantasy path):

| Player | Pos | Team | pass | rush | rec | recs |
|--------|-----|------|------|------|-----|------|
| J.Allen | QB | BUF | 316.3 | 49.7 | 0.0 | 0.0 |
| D.Henry | RB | BAL | 0.0 | 105.6 | 11.3 | 1.2 |
| B.Robinson | RB | ATL | 0.0 | 106.9 | 47.3 | 5.7 |
| D.London | WR | ATL | 0.0 | 0.0 | 129.4 | 9.6 |
| M.Harrison | WR | ARI | 0.0 | 0.0 | 51.9 | 3.9 |

All 24 mixed rows `equal=true` at `player-production-v3-phase3c`.

---

## A4 — Surface smoke (`www.kosedge.com`)

| Surface | HTTP | Notes |
|---------|------|-------|
| `/pro/nfl/fantasy` | 200 | “Fantasy Draft Desk” / Gibbs #1 / Half-PPR. **0** “degraded” / freshness banners. Copy says preseason heavily — matches empty draft-rankings API. |
| `/pro/nfl/props` | 200 | Gate title **“Weekly player props not live — season desk only”**. No degraded banner. |
| `/pro/nfl/projections` | 200 | Loads. No degraded banner. |
| `GET /nfl/fantasy/draft-rankings?season=2026` | 200 `{count:0}` | SoT SUM table empty |
| `GET /nfl/fantasy/rankings?season=2026&week=1` | **500** | Weekly fantasy path not healthy |
| `GET /nfl/props/board?season=2025&week=1` | 200 count 0 | 12 raw rows eligibility-dropped; expected while gated |

Season/fantasy **code** path for draft rankings is SUM weekly baselines cap 17 (`tasks.py` `rn <= 17`). **Prod table is empty**, so the live desk falls back to the launch **preseason bundle** (season-engine / D5-class), not the 3C SUM spine. That is the A4 miss.

No 2026 rows in `nfl_player_game_box_score_sims`. Weekly props LIVE would have no coherent 2026 box-sim board.

---

## B — LIVE go/no-go

**Recommendation: no-go. Leave `NFL_WEEKLY_PROPS_LIVE = false`.**

### B1 — Weekly holdout reprint (Phase 3 → 3C, unchanged)

Structure means + `prop-structure-cal-v1` edge; 2025 w4–17 actual MAE:

| Market | Frozen (P3) | 3B struct-cal | **3C** | Rush regress? |
|--------|-------------|---------------|--------|---------------|
| pass_yds | 50.92 | 51.83 | **51.84** | — |
| rush_yds | 18.17 | 17.98 | **17.98** | **no** |
| rec_yds | 14.99 | 15.54 | **15.26** | — |
| receptions | 0.90 | 0.96 | **0.95** | — |

Pool (prod 2025 cap 17): n≥4000 = **4**, gap **0.097**. Metrics would not block a fire **if** infra + 2026 product path were green.

### B2 — Product rules (not applied)

If LIVE were true: same means on props + fantasy; structure cal edge-only; **no prop PLAY/stake tags**; research/fire framing; season SUM cap 17; disclaimer intact. None of that is flipped here.

### B3 — Exact blockers

**Infra (must fix first)**

1. Worker Online but **not draining** Celery (`models` 1478 / `default` 9 / `odds` 43). Same operational class as `#268` (worker up ≠ worker healthy).
2. **Pending rematerialize** still on `default`: 4× `run_nfl_props_layer_rebuild` + 5× baseline materialize, **no kwargs** (week-22-only wipe class). Revoke before any worker bounce.
3. Stale NFL DR backup (ops-only; not a guest banner). `/nfl/ops/player-layer-coverage` 500s.

**Product / metrics (block LIVE even after drain)**

4. **2026** baselines are pre-3C (Jul 19, 2907 rows/week, gap **0.30**). No 2026 box-sim.
5. `nfl_fantasy_season_draft_rankings` **empty** → fantasy desk is preseason-bundle fallback, not SUM spine.
6. Weekly fantasy rankings API **500**.
7. No approved prop PLAY/stake policy (research edges only if a later fire is approved).

Optional honesty banner on props is already present via the LIVE=false gate. No extra banner shipped.

---

## Residual infra risk

- Bare `rebuild-props-layers?season=` still resolves to `MAX(week)` only. Always pass `weeks=1..18`.
- Worker log CLI only showed the 03:07–03:23 boot window; treat “Online” as insufficient.
- MLB `run_mlb_lineup_nowcast_repricing` is the bulk of the `models` backlog (beat every 10m). After remat revoke, drain or retune beat so NFL remats cannot hide behind MLB nowcast.

---

## Files

- This note
- `nfl-spine-live-smoke-equality-20260820.json`
- `nfl-spine-live-smoke-equality-mixed-20260820.json`
- `.cursor/rules/nfl-production-spine.mdc` — LIVE false after this smoke
