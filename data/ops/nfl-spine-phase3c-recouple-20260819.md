# NFL spine Phase 3C — recouple receiving to pass (2026-08-19/20)

**Status:** ship target-scale recouple / **`NFL_WEEKLY_PROPS_LIVE = false`**  
**PR target:** `deploy-vercel` (post #267 + #268 + prod 3B rematerialize confirmed)  
**Spine version:** `player-production-v3-phase3c`  
**Edge cal:** unchanged `prop-structure-cal-v1`  
**Published means:** raw weekly spine

## Doctrine held

- LIVE stays false
- No PLAY / blend / DK-FD
- No per-player overrides
- Did **not** re-expand QB attempts (pool n≥4000 held)
- Season = SUM spine cap 17

---

## Step 1 — 3B prod baseline (confirmed)

See `data/ops/nfl-spine-phase3b-prod-rematerialize-20260820.md`.

| Metric | 3B prod |
|--------|---------|
| Max QB pass | 4590 |
| QBs ≥ 4000 | 4 |
| Pass↔rec gap | **0.170** |
| Equality | n=40 props==fantasy |

---

## Step 2 — Recouple lever

**Change:** `TEAM_PASS_ATTEMPTS_TARGET_SCALE = 0.92` on the shared
`team_pass_attempts_estimate` used for WR/RB/TE **targets only**.

- Does not change QB attempt schedule / `TEAM_PASS_ATTEMPTS_BASE` (34.8)
- Does not inflate YPR / YAC
- Phase 2 WR1 depth prior unchanged

Rationale: 3B soft-tail compressed QB pass means faster than skill receiving,
which still multiplied `target_proxy × ~34.8×pace×pass`. Damping the target
denom recouples skill volume to the tighter pass budget.

---

## Step 3 — Measure (local holdout + pool)

### Pool (cap 17, 2025)

| Metric | 3B | **3C** |
|--------|-----|--------|
| Max QB pass | 4591 | **4591** (unchanged) |
| QBs ≥ 4000 | 5 / prod 4 | **5** (not worse) |
| Pass↔rec gap | 0.170 | **0.096** |

### Weekly actual MAE (structure means + structure-cal edge)

| Market | 3B struct-cal | **3C** | Δ |
|--------|---------------|--------|---|
| pass_yds | 51.83 | **51.84** | +0.01 |
| rush_yds | 17.98 | **17.98** | 0 |
| rec_yds | 15.54 | **15.26** | **−0.28** |
| receptions | 0.96 | **0.95** | −0.01 |

Reject rules: n≥4000 up ✗ / pass MAE +>1 ✗ / rush regress ✗ — **all clear**.

Equality: n=40, `player-production-v3-phase3c`.

---

## Step 4 — LIVE

| Gate | Result |
|------|--------|
| Gap ≤ ~0.14 | **pass** (0.096) |
| Pool ≤ 5 / ~4591 | **pass** |
| Weekly vs 3B | **pass** (rec improves) |
| **`NFL_WEEKLY_PROPS_LIVE`** | **`false`** |

Pool still has 5 QBs ≥4k locally — healthier gap is not enough alone to fire.

**Go/no-go for Ryan:** Ship 3C for coherence; keep LIVE false until you clear pool + product.

---

## Files

- `nfl_player_projection_engine.py` — `TEAM_PASS_ATTEMPTS_TARGET_SCALE`
- `nfl_player_production.py` — version bump
- `.cursor/rules/nfl-production-spine.mdc` — Phase 3C note
- `nfl-spine-phase3b-prod-rematerialize-20260820.md` — prod parity audit
