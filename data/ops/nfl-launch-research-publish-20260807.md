# Publish launch-current 100k research to guest surfaces — 2026-08-07

## What shipped

| Item | Value |
|------|-------|
| Source research | `data/ops/nfl-season-engine-launch-…-20260807T172531Z/` |
| Web bundle | `data/ops/nfl-preseason-sim-2026-20260807T183534Z/` |
| Pointer | `data/ops/nfl-web-launch-bundle.json` |
| Engine | `nfl-season-engine-v1.12-survivor-planner-ux` |
| N team / player | **100,000** / **1,000** |

Publish script: `scripts/nfl/publish_launch_research_to_web.py`

## Surfaces using launch-current numbers

| Surface | How |
|---------|-----|
| Power ratings | `loadLatestNflPreseasonBundle2026()` → pointer bundle; expected wins + launch banner |
| Fantasy rankings / builder / mock | same loader via `load-desk.ts` |
| Weekly fantasy / projections / DFS | same preseason artifact loader |
| Win distributions | JSON copied into web bundle (`team_win_distributions.json`) |
| Survivor / Game Boxes | live engine API (healthy); desk shows launch-current research notice + engine version |
| Edge Board / Camp | **untouched** |

## Honesty

- Playoff prob = P(wins≥9) from 100k histogram  
- Division / SB probs = softmax display proxies (not full bracket sims)  
- Player playoff CSV empty (REG-only player paths)  
- Preseason labeling on guest banners  

## Go-mode checklist

- [ ] `/pro/power-ratings/nfl` shows Launch 100,000 · DET ~11.31 on top  
- [ ] `/pro/nfl/fantasy` board loads; copy mentions launch-current  
- [ ] `/pro/nfl/survivor` — planner ready, engine v1.12, no false degraded banner  
- [ ] `/pro/nfl/game-boxes` — status OK, launch research notice  
- [ ] `/edge-board/nfl` — still 200, unchanged  
- [ ] `/pro/nfl/camp` — still 200  
- [ ] Freshness probe guest boards not amber from ops-only DR  

## Health (pre-deploy check)

- Railway `/nfl/season-engine/status` → `nfl-season-engine-v1.12-survivor-planner-ux`, survivor capability present  
- `POST /nfl/season-engine/survivor` → 200  

## Files changed

- `scripts/nfl/publish_launch_research_to_web.py` (new)  
- `apps/web/lib/nfl-preseason-artifacts.ts`  
- `apps/web/lib/power-ratings.ts`  
- `apps/web/lib/nfl-launch-research.ts` (new)  
- `apps/web/lib/fantasy/load-desk.ts`  
- `apps/web/app/(pro)/pro/power-ratings/[sport]/page.tsx`  
- `apps/web/app/(pro)/pro/nfl/survivor/page.tsx`  
- `apps/web/app/(pro)/pro/nfl/game-boxes/page.tsx`  
- `data/ops/nfl-preseason-sim-2026-20260807T183534Z/**`  
- `data/ops/nfl-web-launch-bundle.json`  
- `data/ops/nfl-launch-research-sims-current.md`  
- `data/ops/nfl-heavy-research-sim-20260807.md`  
- `data/ops/nfl-launch-research-publish-20260807.md`  
