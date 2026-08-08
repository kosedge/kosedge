# NFL strength wired through engine (2026-08-08)

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Backbone: [`nfl-efficiency-backbone-v1.1-20260808.md`](nfl-efficiency-backbone-v1.1-20260808.md).

## One strength core

| Consumer | Strength path |
|----------|---------------|
| Edge Board / `simulate_nfl_game` | `_load_team_strength_priors` → `efficiency_backbone` (rolling + ST) with packaged v1.1 fill |
| Season engine universe | `load_universe_from_db` / `build_packaged_real_universe` → same priors / packaged backbone → `initialize_strengths` |
| Game boxes | `project_game_player_boxes(universe=…)` — Layer 1 strengths from that universe |
| Survivor plan / week eval | `evaluate_survivor*` on the same `EngineUniverse.strengths` |
| Demo | `build_demo_universe` only — `demo_epa_style_prior` bumps never in real mode |

EPA→index conversion is canonical in `efficiency_backbone.epa_to_strength_indices` (tasks delegates).

## Smoke (local, 2026-08-08)

| Check | Result |
|-------|--------|
| Packaged real strength source | `packaged_efficiency_backbone` for all 32 |
| Packaged version | `v1.1` |
| Demo NE source | `demo_epa_style_prior` (isolated) |
| `simulate_full_season` (2 paths) | OK |
| `evaluate_survivor` week 1 | OK |
| `evaluate_survivor_plan` | OK |
| `project_game_player_boxes` (CAR@CHI W1) | OK |
| Model ≠ KEI / Tag contract | Untouched |

## Prod smoke

| Check | Result |
|-------|--------|
| `model-service` `/health` | 200 ok |
| `model-service` `/health/db` | 200 connected |
| `www.kosedge.com/api/ping` | 200 ok |
| `/pro/nfl/model` UI | Requires deploy of this PR + auth; not blocked at API health layer |

## Explicit non-goals (unchanged)

No KEI reprice rewrite, no Tag policy change, no fantasy UI, no dual parallel ranking API.
