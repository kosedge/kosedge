# NFL spine Phase 3 — season SoT + structure cal + re-gate (2026-08-19)

**Status:** ship structure cal + season SoT / **`NFL_WEEKLY_PROPS_LIVE = false`**  
**PR target:** `deploy-vercel` (post #265)  
**Spine version:** `player-production-v3-phase3`  
**Edge cal:** **`prop-structure-cal-v1`** active (`ACTIVE_PROP_CAL_SOURCE = "structure"`)  
**Published means:** still raw weekly spine (cal = edge math only)

## Doctrine held

- Phase 1 unify + Phase 2 structure knobs remain
- LIVE stays false (promote table: pool still elevated)
- No PLAY / blend / DK-FD changes
- Game board untouched

---

## Step 1 — Rematerialize (prod means = Phase 2 world)

| Season | Features | Baselines (w1–18) |
|--------|----------|-------------------|
| 2023 | 5628 (rebuilt from existing usage) | 5381 |
| 2024 | 5568 (rebuilt) | 5313 |
| 2025 | 5612 (already present) | 5612 rematerialized |

Scripts: `scripts/nfl/rematerialize_features_season.py`, `scripts/nfl/rematerialize_baselines_season.py`

**Equality:** props path == fantasy path, n=40 (`data/ops/nfl-spine-phase3-equality.json`).

**Ops claim:** local DB weekly means now match the Phase 2 holdout world (same knobs). Railway/www need the same rematerialize after merge.

---

## Step 2 — Prior-season feature rebuild

| Item | Value |
|------|-------|
| Source | Existing `nfl_dp_player_usage_weekly` (nflverse PBP already loaded) |
| Writer | `data_platform_nfl.ingest.materialize_player_projection_features` |
| Join keys | `(season, week, team, player_id)` via usage → features → baselines |
| As-of | 2026-08-19 local rematerialize |
| HD odds lake | Not used for features |

Unblocked structure-trained cal (Phase 2 failure mode: 0 feature rows for 2024).

---

## Step 3 — Structure-trained shared cal

Fit: `scripts/nfl/fit_structure_prop_calibration.py`  
Train 2023–24 structure baselines vs actuals (weeks 4–17). Holdout 2025.

| Market | Structure-only actual MAE | Frozen actual | **Structure-cal actual** | Frozen close | **Struct-cal close** |
|--------|---------------------------|---------------|--------------------------|--------------|----------------------|
| pass_yds | 57.53 | 50.95 | **50.92** | 17.96 | 18.04 |
| rush_yds | 19.86 | 18.88 | **18.17** | 12.71 | **11.70** |
| rec_yds | 16.21 | 16.40 | **14.99** | 12.42 | **11.13** |
| receptions | 0.97 | 1.00 | **0.90** | 1.14 | **1.10** |

**Intercepts (`prop-structure-cal-v1`):**

| Market | Frozen | Structure |
|--------|--------|-----------|
| pass_yds | −8.5 | **−12.0** (clamp max) |
| rush_yds | +3.6 | **−2.087** |
| rec_yds | +1.6 | **−4.431** |
| receptions | +0.12 | **−0.342** |

**Decision:** activate structure cal for **edge math** (`ACTIVE_PROP_CAL_SOURCE = "structure"`). Rush actual improves vs structure-only and vs frozen. Pass close essentially tied.

Artifact: `data/ops/nfl-spine-phase3-structure-cal.json`

---

## Step 4 — Season / futures = spine SoT

| Change | Where |
|--------|-------|
| Cap season SUM at **17** game-rows | `_fetch_season_player_totals` (draft/awards); `aggregate_weekly_projection_rows` |
| Disable QB-lock / skill-prior / team-budget overlays by default | `generate_player_regular_season_totals` + CSV writer |
| D5 MC player totals | Documented research-only in `season_sim.py` — not desk SoT |

### Season pool (2025 baselines)

| Check | Before (uncapped) | After (cap 17, spine sum) |
|-------|-------------------|---------------------------|
| Max QB pass | 4843 (Stafford, 20 games) | **4790** (Prescott, 17) |
| QBs ≥ 4000 | 9 | **7** |
| Pass↔rec gap | 0.127 | 0.137 |

Gap not yet under the old ~28% stored-era figure’s “tight” target in absolute terms, but overlays no longer invent a second optimistic pool. Remaining ≥4k counts are high per-game means × 17 — further volume work is post-Phase-3.

---

## Step 5 — Full promote gates → LIVE

Holdout post rematerialize + Phase 2 structure + structure-cal (edge):

| Market | vs close (struct-cal vs frozen) | vs actual (struct-cal vs frozen) | residual toward 0 | rush rule |
|--------|----------------------------------|----------------------------------|-------------------|-----------|
| pass_yds | ≈tied (18.04 vs 17.96) | **pass** (50.92 ≤ 50.95) | yes | — |
| rush_yds | **pass** (11.70 < 12.71) | **pass** (18.17 < 18.88) | yes | **pass** vs structure-only |
| rec_yds | **pass** | **pass** | yes | — |
| receptions | **pass** | **pass** | yes | — |

### Buckets (structure means + frozen diagnostics)

| Slice | Frozen residual vs actual |
|-------|---------------------------|
| Pass 225–274 | −3.6 |
| RB1 | **−0.24** |
| Rec 8+ | −4.2 |

### LIVE decision

| Gate | Result |
|------|--------|
| Core cal/structure gates | Mostly green |
| Season pool not insane | **Soft fail** — 7 QBs ≥4000 still elevated |
| Spine equality | **pass** (n=40) |
| **`NFL_WEEKLY_PROPS_LIVE`** | **`false`** |

Ship cal + SoT progress; no fire language on site until pool is tighter / you greenlight LIVE after audit.

---

## Step 6 — Product honesty

- Props UI remains gated (`NFL_WEEKLY_PROPS_LIVE = false`); research framing
- Fantasy weekly/season/draft read same spine means; season capped at 17
- No prop PLAY tags in this PR
- After merge: rematerialize features+baselines on Railway/worker for seasons you serve; regenerate season CSVs if hub uses them

---

## Remaining gaps (post-merge)

1. In-season injury / rolling usage path still separate from this offline rebuild  
2. Rec 8+ residual ~−4 still open (usage share fine-tune)  
3. Season ≥4k count — needs further per-game volume or efficiency, not another intercept  
4. D5 team W/L can stay MC; do not republish engine player yards as futures SoT  
5. Confirm www worker rematerialize so production DB matches this holdout world

## Artifacts

- `data/ops/nfl-spine-phase3-structure-cal.json`
- `data/ops/nfl-spine-phase3-pool-before.json` / `…-after.json`
- `data/ops/nfl-spine-phase3-equality.json`
- `scripts/nfl/rematerialize_features_season.py`
- `scripts/nfl/fit_structure_prop_calibration.py`
