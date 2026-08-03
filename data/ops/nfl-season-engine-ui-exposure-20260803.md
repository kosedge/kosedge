# NFL Season Engine — First UI Exposure

**Date:** 2026-08-03  
**Engine:** `nfl-season-engine-v1.4.1-hardened` (Railway model-service)  
**Web branch:** `feat/nfl-season-engine-ui` → `deploy-vercel`

## Shipped routes

| Route | Job |
| --- | --- |
| `/pro/nfl/model` | Small hub linking the two tools + live engine version |
| `/pro/nfl/game-boxes` | Future matchup picker + projected player boxes |
| `/pro/nfl/survivor` | Used-team chips + week selector + ranked survivor picks |

Nav: NFL tools menu (`Season Model`, `Game Boxes`, `Survivor`) and Betting Desk overview cards.

## BFF (no browser → Railway secrets)

| Method | Path | Upstream |
| --- | --- | --- |
| `GET` | `/api/nfl/season-engine/status` | `GET /nfl/season-engine/status` |
| `GET`/`POST` | `/api/nfl/season-engine/game-boxes` | `GET`/`POST /nfl/season-engine/game-boxes` |
| `POST` | `/api/nfl/season-engine/survivor` | `POST /nfl/season-engine/survivor` |

Uses `MODEL_SERVICE_URL` + `INTERNAL_API_SECRET` server-side only (`x-kosedge-secret`).

## Exposed vs still API-only

**Exposed in UI**

- Game-box distributions (p50 + p10–p90) for QB/RB/WR/TE
- Optional star-out injury scenario (demo named cores: KC/BUF/PHI/SF/DET)
- Survivor ranked picks (`win_rate`, `save_score`, `pick_now_score`)
- Status / engine version on hub

**Still API / CLI only**

- Full-season `POST /nfl/season-engine/simulate`
- Rich `include_diagnostics` explain payloads (usage shares, share integrity, etc.)
- Arbitrary multi-player / multi-week injury path builders
- Heavy CLI runs (`n_sims` beyond HTTP caps)

## Defaults & gotchas

- Game boxes: `n_replicates=50` (engine minimum)
- Survivor: `n_sims=200`, `top_n=16`
- Live Railway currently returns **`mode=demo`** (round-robin placeholder schedule; sparse named skill cores). UI banners this honestly.
- Matchup picker prefers fair-lines upcoming slate; falls back to team dropdowns when empty.
- Injury toggle builds a single-week `status=out` path; baseline vs injured tables shown side-by-side when selected.
- Edge Board / KEI / Model-vs-KEI paths unchanged.

## Contract

See `data/ops/nfl-season-engine-api-contract-20260803.md`.
