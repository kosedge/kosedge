# NFL Week 1 — live still FAIL after #403 (2026-09-02)

**PR target:** `deploy-vercel` (do not merge — CoS merges)  
**Branch:** `cursor/nfl-fair-lines-melbourne-live-1b4e`  
**Live Railway sha:** `639b0ae31843` (#403) still failed.

## Production evidence

`diagnostics.kei_week1_reprice.game_card_source = failed`, `game_card_count = 0`.
SF@LAR: `same-coast=1 Melbourne=0 visual_crossing=1`, `venue=null`, `start_time=2026-09-10T20:00:00Z`.

Root cause: Railway image has no `apps/web` canonical JSON (`parents[4]` → `/`). Schedule cards had no venue → `_international` never set → or entire card build failed → legacy LA path.

Game Boxes: `503 nfl_game_boxes_spine_overlay_miss` with `UndefinedColumn total_tds_mean` (baselines table lacks that column; box sims have it). Transaction abort blocked props-edges fallback.

## Fixes

1. `nfl_week1_game_cards.py` — bake Melbourne; index `(LAR, SF)` like the route; copy canonical JSON into model-service data.
2. Fair-lines uses `build_week1_game_cards` only; reprice fail-closes SF@LAR even if `game_card=None`.
3. Game Boxes SELECT drops `total_tds_mean`; rollback before fallback.
4. Tests call route keys `(LAR, SF)` — no hand-set `_international`.

Live route for boxes: `GET /nfl/season-engine/game-boxes` (www: `/api/nfl/season-engine/game-boxes`).
