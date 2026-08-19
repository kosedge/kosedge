# NFL spine Phase 3B — prod parity + season pool tighten (2026-08-19)

**Status:** ship pool compression + prod rematerialize path / **`NFL_WEEKLY_PROPS_LIVE = false`**  
**PR target:** `deploy-vercel` (post #266)  
**Spine version:** `player-production-v3-phase3b`  
**Edge cal:** unchanged **`prop-structure-cal-v1`** (`ACTIVE_PROP_CAL_SOURCE = "structure"`)  
**Published means:** raw weekly spine (cal = edge math only)

## Doctrine held

- Phase 1–3 spine + structure cal unchanged on edge math
- LIVE stays false (pool improved but not clear + pass MAE edge-up)
- No PLAY / blend / DK-FD changes
- No per-QB overrides or residual hacks
- Season/futures SoT = SUM spine cap 17

---

## Step 1 — Prod / worker rematerialize (A)

### Local parity proof (same knobs as code)

| Season | Features | Baselines rematerialized (w1–18) |
|--------|----------|----------------------------------|
| 2023 | 5628 (Phase 3 rebuild) | 5381 ✓ Phase 3B |
| 2024 | 5568 (Phase 3 rebuild) | 5313 ✓ Phase 3B |
| 2025 | 5612 | 5612 ✓ Phase 3B |

Scripts: `rematerialize_features_season.py` (features unchanged from #266), `rematerialize_baselines_season.py` (re-run all three seasons with 3B knobs).

**Equality:** props == fantasy, n=40, `player-production-v3-phase3b` (`data/ops/nfl-spine-unify-phase1-equality.json`).

**Pool (cap 17, honest query):** see Step 4 before/after.

### Railway / www (post-merge)

1. Merge deploys model-service with 3B engine knobs.
2. Worker DB rematerialize (one season at a time):

```bash
curl -X POST "https://model-service-production-e253.up.railway.app/nfl/ops/rebuild-props-layers?season=2023&model_version=nfl-player-v1"
curl -X POST "https://model-service-production-e253.up.railway.app/nfl/ops/rebuild-props-layers?season=2024&model_version=nfl-player-v1"
curl -X POST "https://model-service-production-e253.up.railway.app/nfl/ops/rebuild-props-layers?season=2025&model_version=nfl-player-v1"
```

3. Regenerate hub season CSVs if bundle uses `player_regular_season_totals.csv` (`regen_player_season_totals.py` against live DB).

**Note:** Pre-merge prod rebuild uses Phase 3 engine only; true prod parity requires post-merge rematerialize above.

---

## Step 2 — Diagnose season pass richness (B)

**Why n≥4000 was 7 at cap-17 (Phase 3 reference):**

| Root cause | Evidence |
|------------|----------|
| **Per-game elite attempt schedule too hot** | Prescott cap-17 avg **281.8 pass yds/g**, **40.4 att/g** (~41.5 cap); YPA ~7.0 is fine |
| **Not cap-17 failure in product SoT** | Raw DB has 20+ rows for some QBs (Stafford 20, Maye 21); `_fetch_season_player_totals` + CSV aggregator cap at 17 |
| **Not team budget incoherence alone** | Skill rec trails QB pass on several teams (DAL gap ~18%) because pass volume was high, not double-count |
| **Not YPA overshoot** | Elite YPA ~6.8–7.0; problem is attempts × YPA |
| **Not residual hack candidate** | Structural attempt compression only |

### Top 12 QB season pass (cap 17) — **before** 3B

| Player | Team | Season pass | Games | Avg pass/g | Att/g | Team QB pass | Skill rec |
|--------|------|-------------|-------|------------|-------|--------------|-----------|
| D.Prescott | DAL | 4790 | 17 | 281.8 | 40.4 | 4828 | 5712 |
| J.Goff | DET | 4535 | 17 | 266.7 | 38.9 | 4543 | 4932 |
| M.Stafford | LA | 4479 | 17 | 247.1 | 35.1 | 4479 | 5507 |
| T.Lawrence | JAX | 4161 | 17 | 232.1 | 34.3 | 4178 | 4947 |
| C.Williams | CHI | 4139 | 17 | 232.6 | 33.6 | 4153 | 4962 |
| B.Mayfield | TB | 4126 | 17 | 229.5 | 33.7 | 4135 | 4542 |
| B.Nix | DEN | 4094 | 17 | 228.3 | 33.4 | 4212 | 5045 |
| J.Allen | BUF | 3914 | 17 | 219.5 | 31.5 | — | — |
| P.Mahomes | KC | 3817 | 14 | 272.6 | 39.5 | — | — |
| D.Maye | NE | 3809 | 17 | 214.0 | 30.5 | — | — |
| J.Herbert | LAC | 3772 | 17 | 210.5 | 32.4 | — | — |
| J.Love | GB | 3726 | 16 | 232.8 | 33.3 | — | — |

---

## Step 3 — Structural pool tighten

**Levers (smallest set, no name edits):**

| Knob | Phase 3 | Phase 3B |
|------|---------|----------|
| `TEAM_PASS_ATTEMPTS_BASE` | 35.2 | **34.8** |
| QB attempt intercept / slope | 18.6 + 31.8× | **18.2 + 30.8×** |
| Hard attempt cap | 41.5 | **40.2** |
| Upper-tail soft compression | none | **above 35.5 att, ×0.88 tail** |

Phase 2 RB1 / WR1 knobs untouched. `prop-structure-cal-v1` intercepts unchanged (edge-only).

`props_confidence_diagnosis._season_pool` now uses **cap-17** sums (was inflating n≥4000 when DB had 18–21 game rows).

---

## Step 4 — Holdout + pool before → after

### Weekly holdout 2025 w4–17 (structure means + structure-cal edge)

| Market | Phase 3 struct-only actual | Phase 3 struct-cal actual | **3B struct-only** | **3B struct-cal** | Δ cal vs P3 |
|--------|---------------------------|---------------------------|--------------------|--------------------|-------------|
| pass_yds | 57.53 | **50.92** | 61.57 | **51.83** | +0.91 |
| rush_yds | 19.86 | **18.17** | 19.57 | **17.98** | **−0.19** |
| rec_yds | 16.21 | **14.99** | 16.49 | **15.54** | +0.55 |
| receptions | 0.97 | **0.90** | 1.00 | **0.96** | +0.06 |

Rush actual **improves**; pass/rec edge-up modestly (~1 yd pass MAE). No material rush regression.

### Season pool (cap 17)

| Metric | Phase 3 (#266) | **Phase 3B** |
|--------|----------------|--------------|
| Max QB pass | 4790 | **4591** |
| QBs ≥ 4000 | 7 | **5** |
| Pass↔rec gap (mean) | 0.137 | 0.172 |

Gap widened because pass compressed faster than receiving corps (expected when only QB volume knob moves).

Artifacts: `nfl-spine-phase3b-pool-before.json`, `nfl-spine-phase3b-pool-after.json`

---

## Step 5 — LIVE recommendation

| Gate | Result |
|------|--------|
| Prod parity (local) | **pass** — 2023–25 rematerialized, equality n=40 |
| Prod parity (Railway) | **pending post-merge** rematerialize |
| Pool not elevated | **soft pass** — 5 QBs ≥4k (was 7; target low single digits) |
| Weekly gates vs Phase 3 cal | **soft pass** — rush better; pass +0.9 MAE |
| Spine equality | **pass** |
| **`NFL_WEEKLY_PROPS_LIVE`** | **`false`** |

**Go/no-go for Ryan:** Pool materially healthier (7→5, max −199 yds) without wrecking rush weekly gates. Pass MAE ticked up ~1 yd with frozen cal — acceptable for structure progress but **not** enough to fire props LIVE. Re-fit structure cal only if a candidate beats Phase 3 on pass **and** pool; default stay gated.

---

## Step 6 — Files touched

- `services/model-service/src/services/nfl_player_projection_engine.py` — 3B attempt compression
- `services/model-service/src/services/nfl_player_production.py` — version bump
- `scripts/nfl/props_confidence_diagnosis.py` — cap-17 pool metric
- `.cursor/rules/nfl-production-spine.mdc` — Phase 3B note

## Artifacts

- `data/ops/nfl-spine-phase3b-prod-pool-20260819.md` (this file)
- `data/ops/nfl-spine-phase3b-pool-before.json` / `-after.json`
- `data/ops/nfl-spine-unify-phase1-equality.json`
- `data/ops/nfl-props-confidence-diagnosis.json`
