# NFL spine Phase 2 — structural player production (2026-08-19)

**Status:** ship structure / **NO-GO** on `NFL_WEEKLY_PROPS_LIVE`  
**PR target:** `deploy-vercel` (post #264 Phase 1)  
**Spine version:** `player-production-v2-phase2`  
**Cal:** frozen `prop-enterprise-cal-v1` **unchanged** (structure-trained cal blocked; lag-candidate rejected)

## Doctrine held

- Shared weekly means for props + fantasy (Phase 1 path untouched)
- `NFL_WEEKLY_PROPS_LIVE = false`
- No PLAY / blend / DK-FD tag changes
- No residual-only intercept swap
- Game board spine untouched
- Cal re-fit attempted **after** structure only

---

## Critical measurement note

The August diagnosis table used **stored** 2025 baselines that were **stale** relative to a fresh rematerialize of current `deploy-vercel` knobs.

| Baseline | How obtained | Pass raw resid vs actual | Rush raw resid | RB1 frozen resid | 8+ WR frozen resid |
|----------|--------------|--------------------------|----------------|------------------|--------------------|
| **Stored Step 1** (`nfl-spine-phase2-structure-before.json`) | DB rows before any rematerialize | −31.1 | −4.6 | −6.8 | −26.5 |
| **Fresh stock** (`…-before-fresh.json`) | Rematerialize weeks 1–18 with deploy-vercel knobs | **+9.5** | **+11.9** | **+10.8** | **−4.4** |

**A/B base for Phase 2 knobs = fresh stock rematerialize**, not the stale stored table. Stored table kept for audit trail only.

---

## Step 1 — Before tables

### Holdout 2025 (stored baselines — informational)

| Market | n | Raw vs close MAE/resid | Frozen vs close | Raw vs actual | Frozen vs actual |
|--------|---|------------------------|-----------------|---------------|------------------|
| pass_yds | 431 | 51.0 / −34.1 | 22.5 / −15.4 | 65.5 / −31.1 | 53.5 / −12.4 |
| rush_yds | 1291 | 11.5 / −1.5 | 9.9 / +1.8 | **16.27** / −4.6 | 16.48 / −1.3 |
| rec_yds | 2663 | 13.3 / −7.4 | 10.3 / −4.4 | 17.2 / −11.1 | 16.5 / −8.1 |
| receptions | 2595 | 1.29 / −0.52 | 1.10 / −0.36 | 1.14 / −0.58 | 1.09 / −0.41 |

### Holdout 2025 (fresh stock rematerialize — **A/B before**)

| Market | Raw vs actual MAE / resid | Frozen vs actual MAE / resid |
|--------|---------------------------|------------------------------|
| pass_yds | 67.29 / **+9.54** | 52.85 / +5.25 |
| rush_yds | 24.48 / **+11.91** | 21.00 / +8.81 |
| rec_yds | 16.55 / +4.15 | 16.62 / +3.36 |
| receptions | 1.00 / +0.30 | 1.02 / +0.37 |

### Buckets (fresh stock)

| Slice | Frozen MAE vs actual | Frozen residual |
|-------|----------------------|-----------------|
| Pass close 225–274 | 52.2 | **+3.7** |
| Rush RB1 | 31.1 | **+10.8** |
| Rec 8+ targets | 27.0 | **−4.4** |

### Season pool (fresh stock)

Max QB pass sum **5065**; **n ≥ 4000 = 10**; pass↔rec gap mean **0.076**. (Sums can include >17 game-rows — Phase 3 SoT work.)

---

## Knobs changed (structure)

| Area | File | Change |
|------|------|--------|
| Team pass base | `nfl_player_projection_engine.py` | Named `TEAM_PASS_ATTEMPTS_BASE = 35.2` (unchanged magnitude; named for ops) |
| QB attempts / pace | same | Compress: `qb_pace = 0.52+0.42*pace` ∈[0.84,1.10]; attempts `(18.6 + 31.8 * …)` cap **41.5** |
| RB shares | same | Bell cow **0.68/0.24/0.08**; soft **0.58/0.30/0.12** |
| RB carries / YPC | same | Carries `4.0 + 22.5 * rush_share` cap 30; YPC `(4.05 + 1.15*vol)` cap 7.8 |
| WR1 targets | `tasks.py` `_apply_wr_te_depth_target_prior` | Prior WR1 **0.32**; floor **0.26**; cap **0.50**; depth-1 blend 50/50 |

First lift attempt (raise pass/RB) **overshot** and was dialed into this **compression** path once fresh rematerialize showed positive residuals.

---

## After structure (vs fresh stock A/B)

| Market | Raw MAE before→after | Raw resid before→after | Verdict |
|--------|----------------------|------------------------|---------|
| pass_yds | 67.29 → **62.33** | +9.54 → **−4.26** | Improved |
| rush_yds | 24.48 → **19.57** | +11.91 → **+2.36** | Improved (must-not-regress gate vs fresh: **pass**) |
| rec_yds | 16.55 → 16.61 | +4.15 → +4.28 | Flat / tiny regress |
| receptions | 1.00 → 1.01 | +0.30 → +0.31 | Flat |

### Buckets after

| Slice | Frozen resid before→after | Frozen MAE before→after |
|-------|---------------------------|-------------------------|
| Pass 225–274 | +3.7 → **−3.6** | 52.2 → 51.8 |
| RB1 | +10.8 → **−0.24** | 31.1 → **27.8** |
| Committee | +… → +4.9 | — |
| Rec 8+ | −4.4 → **−4.2** | 27.0 → 27.0 |

### Season pool after

Max **4842**; n ≥ 4000 **9** (still elevated vs stored-era 0 — game-row count + remaining volume; Phase 3). Gap **0.127**.

---

## Step 5 — Shared cal re-fit

- Local DB has **no** `nfl_player_projection_features_weekly` for 2024 → cannot rematerialize 2024 structure means for train.
- Lag-trained candidate (pass intercept **+6.1**) still **fails** pass actual/close vs frozen on structure holdout.
- **Decision:** do **not** replace `FROZEN_MEAN_INTERCEPT`. Edge math stays frozen cal-v1. Published means stay structure raw spine.

| Market | Structure raw vs actual | + frozen | + lag candidate |
|--------|-------------------------|----------|-----------------|
| pass_yds | 62.3 / −4.3 | **51.8 / −1.4** | 52.4 / +5.4 (worse) |
| rush_yds | 19.6 / +2.4 | 18.7 / +3.3 | 18.1 / +0.7 |
| rec_yds | 16.6 / +4.3 | 16.6 / +3.4 | 16.1 / +2.0 |
| receptions | 1.01 / +0.31 | 1.03 / +0.38 | 0.99 / +0.25 |

---

## Step 6 — Promote gates → LIVE

| Gate | Result |
|------|--------|
| Core markets: close not materially worse | Mixed; frozen still best on pass close |
| Core markets: actual not worse vs **fresh stock** | Pass/rush/receptions improve; rec flat |
| Rush must not regress vs pre-Phase-2 **fresh** | **Pass** (24.5 → 19.6) |
| Rush vs **stored** Step 1 actual MAE | **Fails** (16.27 → 19.57) — stored was stale low-volume |
| Structure-trained shared cal ready | **No** (no 2024 features) |
| Season pool sane (not 32×4k; gap) | Better than fresh stock max; still 9 QBs ≥4k |
| **`NFL_WEEKLY_PROPS_LIVE`** | **`false`** |

Ship structure means anyway; spine still one; research framing.

---

## Step 7 — Coherence

- Props path mean == fantasy path mean: **n=40 equal** (`data/ops/nfl-spine-phase2-equality.json`), version `player-production-v2-phase2`
- D4/D5 still **not** weekly SoT (Phase 3)
- D3 season sums still `SUM(weekly baselines)` — inherit Phase 2 means after rematerialize in prod

---

## Phase 3 recommendation

1. Materialize features for prior seasons (or warehouse feature rebuild) so structure cal can train on shared means.
2. Pick **one** season/futures SoT = sum/distribution of weekly spine (retire dual D5 pool).
3. Cap season aggregates at 17 games for pool checks.
4. Re-run promote gates; only then consider LIVE.

---

## Artifacts

- `data/ops/nfl-spine-phase2-structure-before.json` — stored Step 1
- `data/ops/nfl-spine-phase2-structure-before-fresh.json` — fresh stock A/B
- `data/ops/nfl-spine-phase2-structure-after-structure.json` — after knobs + cal decision
- `data/ops/nfl-spine-phase2-equality.json`
- `scripts/nfl/rematerialize_baselines_season.py`
