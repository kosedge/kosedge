# Edge Board Layout Unsmush + Week 1 / Full Slate Tabs — 2026-08-10

**Branch:** `feat/edge-board-layout-tabs` → `deploy-vercel`  
**Baseline tip:** #173 `99fb3f53` (matchup overviews + Stat Drop)

## Owns / does not own

| Owns | Does not own |
|------|----------------|
| Row density / Stat Drop expand-in-flow | New model math |
| Week 1 vs Full slate tabs + URL `?slate=` | Props / mock CPU / kicker |
| Honest empty Week 1 (no fallthrough) | Sim depth |

## Before → after

| Before | After |
|--------|--------|
| Absolute Overview/Stats overlays covered the next matchup | In-flow expand row pushes content down |
| Crushed row rhythm; site labels collided with lines | Wider Game/Time columns, `py-5`, clearer site/kickoff stack |
| Stat Drop horizontal one-liner on mobile | 2×N grid (4/8 cols as space allows) |
| “Current week” / “Odds slate” | **Week 1** (default) / **Full slate** with counts |
| Empty current week could nearest-week fallthrough | Week 1 tab: strict REG week 1 only; empty stays empty |

## URL

- Default / `?slate=week1` (aliases: `live`, missing)
- `?slate=full` (alias: `all`)

## Smoke

1. `/edge-board/nfl` → Week 1 selected by default  
2. Open Stats on any row → next game fully visible below the Stat Drop strip  
3. Switch Full slate → multi-week list  
4. Mobile width → tap targets ≥44px; Stat Drop 2-column grid  

## Preserved from #173

Week-1 form ban · Neutral/Melbourne · Power on every Stat Drop · PLAY = KEI vs market
