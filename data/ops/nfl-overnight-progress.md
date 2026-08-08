# NFL overnight progress — efficiency backbone A→C

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Started: 2026-08-08 (overnight autonomous run).

---

## Phase A — Land Sprint 2

| Field | Value |
|-------|--------|
| Timestamp | 2026-08-08T05:18:00Z (approx; verified 05:18 local continue) |
| Status | **PASS** |
| PR #135 | MERGED 2026-08-08T05:00:46Z → `deploy-vercel` ([url](https://github.com/kosedge/kosedge/pull/135)) |
| Deploy | Vercel auto-deploys from `deploy-vercel` (no manual trigger required). Railway model-service was rebuilding after merge. |
| Materialize | `scripts/nfl/materialize_team_rolling_features.py --seasons 2023,2024,2025,2026` against Railway public DSN |
| Precondition fix | Railway situational was empty; synced 2286 rows from local (2023–2026) then rematerialized rolling |

### Railway row counts (after materialize)

| Table | Count |
|-------|------:|
| `nfl_dp_team_situational_weekly` | 2286 |
| `nfl_dp_team_rolling_features_weekly` | 2286 (2023:570, 2024:570, 2025:570, 2026:576; 32 teams each) |
| `nfl_dp_team_rolling_features_latest` | 32 |

### Smell tests

- Packaged backbone pytest: **13 passed** (`test_nfl_efficiency_backbone.py` + packaged EPA)
- SEA ≫ ARI (composite gap holds)
- NE top-tier (≤ rank 10)
- Demo bumps demo-only

### Next

Phase B — v1.1 ST + true EPA splits on `feat/nfl-efficiency-backbone-v1.1`.

---

## Phase B — Efficiency v1.1

| Field | Value |
|-------|--------|
| Timestamp | 2026-08-08T05:30Z (approx) |
| Status | **PASS** |
| Branch | `feat/nfl-efficiency-backbone-v1.1` |
| ST | Built `nfl_dp_team_st_kav_weekly` on local + Railway (7124 rows) |
| Splits | Pass/run/early-down EPA from `nfl_dp_play_by_play` into packaged backbone |
| Artifact | `nfl_team_efficiency_backbone_2026.json` version **v1.1** (32/32 ST + splits) |
| Tests | **15 passed** (`test_nfl_efficiency_backbone.py` + packaged EPA) |
| Ops note | [`nfl-efficiency-backbone-v1.1-20260808.md`](nfl-efficiency-backbone-v1.1-20260808.md) |

### Before/after sample

| Team | v1.1 o/d/comp | st_index | Rank |
|------|---------------|----------|------|
| SEA | 1.026 / 1.144 / **2.170** | 1.037 | 2 |
| ARI | 0.946 / 0.898 / **1.844** | 0.912 | 27 |
| NE | 1.068 / 1.094 / **2.162** | 0.912 | 3 |

Top 8: LA, SEA, NE, HOU, DEN, BUF, JAX, PHI. SEA−ARI gap ~0.326.

### Next

Phase C — confirm one strength core through season engine / survivor / boxes.

---

## Phase C — Wire strength through season engine

| Field | Value |
|-------|--------|
| Timestamp | 2026-08-08T05:35Z (approx) |
| Status | **PASS** (local + prod health) |
| Real strength source | `packaged_efficiency_backbone` / `efficiency_backbone` only (no demo in real) |
| Version on packaged | `v1.1` |
| Local smoke | season sim, survivor week+plan, game boxes CAR@CHI W1 — OK |
| Prod | `/health` 200, `/health/db` connected, `kosedge.com/api/ping` 200 |
| Ops note | [`nfl-strength-wired-through-engine-20260808.md`](nfl-strength-wired-through-engine-20260808.md) |
| KEI / Tag | Untouched |

### Final smoke checklist

| Item | Pass/Fail |
|------|-----------|
| PR #135 merged → deploy-vercel | PASS |
| Railway rolling populated (2286 / latest 32) | PASS |
| Smell SEA ≫ ARI, NE top tier | PASS |
| Demo bumps demo-only | PASS |
| v1.1 ST + true splits in package | PASS |
| Thin splits labeled | PASS |
| Season engine uses same strength slot | PASS |
| Survivor + game boxes smoke | PASS |
| Model-service health / DB | PASS |
| `/pro/nfl/model` authenticated UI | PENDING deploy of v1.1 PR |

### Remaining gaps

- Rolling live path still lacks week-aligned pass/run/early EPA (packaged has them; rolling has overall 5g + ST).
- ST play counts approximated for labeling.
- QB premium still hook-only.


---

## End-of-night

| Field | Value |
|-------|--------|
| Timestamp | 2026-08-08T12:26:03.735190+00:00 |
| v1.1 PR | https://github.com/kosedge/kosedge/pull/138 — MERGED into deploy-vercel |
| Overall | **A PASS · B PASS · C PASS** (UI auth spot-check pending after deploy) |

Morning: Vercel should auto-deploy `deploy-vercel`. Spot-check `/pro/nfl/model` + Edge Board when logged in.

---

## True PR foundation (morning follow-on — 2026-08-08)

| Field | Value |
|-------|--------|
| Status | PR open → `deploy-vercel` |
| PR | https://github.com/kosedge/kosedge/pull/140 |
| Ops note | [`nfl-true-pr-foundation-20260808.md`](nfl-true-pr-foundation-20260808.md) |
| Change | Live `_load_team_strength_priors` uses gradual prior→current blend (`games/8`); kills hard switch at `completed_reg >= 1`. Full-strength vs current PR split + drivers/stubs. Edge Board prefers same core as season engine. |
| Tests | `test_nfl_true_pr_foundation.py` + backbone/packaged — 26 passed locally |

---

## Past SOS / Adjusted Strength of Competition (2026-08-08)

| Field | Value |
|-------|--------|
| Status | PR → `deploy-vercel` (on top of merged #140 + #141) |
| Ops note | [`nfl-adjusted-sos-past-20260808.md`](nfl-adjusted-sos-past-20260808.md) |
| Change | Prior packages schedule-adjusted via time-of-game opponent efficiency (rolling W−1, else approximate season). Soft/hard slate polarity; future 2026 SOS excluded from intrinsic PR. |
| Tests | `test_nfl_adjusted_sos_past.py` + true PR / backbone / player regression — 45 passed locally |
