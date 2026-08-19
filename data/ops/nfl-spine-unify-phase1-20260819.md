# NFL spine unify — Phase 1 (2026-08-19)

**Status:** implement / ship  
**Branch target:** `deploy-vercel`  
**Go/no-go:** `NFL_WEEKLY_PROPS_LIVE` stays **false**. No residual re-fit. No pass-only intercept swap.

## What Phase 1 does

Unify the **weekly read path** so props and fantasy share one player-game production vector:

| Surface | Before | After (Phase 1) |
|---------|--------|-----------------|
| Props board published `model_mean` | baseline ⊕ box MC blend → walk-forward or frozen cal | **raw baselines** via `production_from_baseline_row` |
| Props edge math | cal applied onto blended mean | **frozen** `prop-enterprise-cal-v1` once onto spine mean; published mean unchanged |
| Fantasy weekly | raw baselines → `fantasy_points_from_projection` | **same helper** `production_from_baseline_row` → scoring |
| Box MC | preferred published mean | **research-only** in prop diagnostics (`box_research`) |

Shared module: `services/model-service/src/services/nfl_player_production.py`  
Version string: `player-production-v1-phase1`

## Exit proof (strict)

Script: `scripts/nfl/spine_unify_phase1_equality.py`  
JSON: `data/ops/nfl-spine-unify-phase1-equality.json`  
Unit lock: `services/model-service/tests/test_nfl_player_production_phase1.py`

Requirement: for ≥ **20** players, props-path mean == fantasy-path mean for the same `(season, week, player)` production fields (`pass_yds`, `rush_yds`, `rec_yds`, `receptions`). Equality is via the shared helper both materializers call — not “we intend to.”

**Sample proof (2026-08-19):** local DB `nfl_player_projection_baselines` season=2025 week=1 — **n=40, n_equal=40, n_mismatch=0** (`row_source=database`). See `nfl-spine-unify-phase1-equality.json`.

## Frozen cal rule

- May apply **once** on the shared vector for **edge math only**.
- Must **not** re-fit walk-forward intercepts in Phase 1.
- Must **not** pass-only swap / residual-only candidate from the confidence diagnosis.

## Untouched (by design)

- Game board spine (spread / total / KEI) — separate.
- PLAY band `spread_play_v2_cap7` (2.5 ≤ \|edge\| < 7.0).
- DK → FD → consensus stake-close tagging (best column shop-only).
- `NFL_WEEKLY_PROPS_LIVE = false`.
- Blend weights 0.30 / 0.30.

## D4 / D5 — documented, **not** SoT until Phase 3

Phase 1 demotes these as weekly/player-production SoT. Phase 3 **must pick one SoT** — do not leave fantasy season on baselines and futures on season-engine forever.

| ID | Surface | Exact touch points | Phase 1 status |
|----|---------|--------------------|----------------|
| **D4** | Season box sims | `aggregate_game_sims_to_season` in `nfl_player_box_score_simulator.py`; table `nfl_player_season_box_score_sims`; materialize path in `tasks.py` (season box aggregate) | **Not weekly SoT.** Research / sim pool only. |
| **D5** | Season engine / futures | `nfl_season_engine` + `offensive_production_stack`; futures consumers that read season-engine production | **Not player-production SoT.** Documented demotion until Phase 3 chooses one promote path. |
| **D3** (related) | Fantasy season / draft | `_fetch_season_player_totals` — `SUM(weekly baselines)` in `tasks.py` | Still baseline sum for now; Phase 3 must align with chosen SoT (not dual forever). |

## Phase 2 (wait for greenlight after merge)

Structural order only — do not start until Phase 1 is merged and greenlit:

1. Team pass budget / QB script  
2. RB1 usage  
3. High-target WR (8+ targets)  
4. **Then** one shared cal  

No residual-only. No props-live unlock on close MAE alone.

## Phase 3 / 4 reminder

- Phase 3: season + futures = sum/distribution of the spine; **pick one SoT**.
- Phase 4: one unlock of **player production vN** (not two products).
