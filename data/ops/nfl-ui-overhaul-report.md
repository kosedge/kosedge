# NFL UI Overhaul Report

**Date:** 2026-07-31  
**Branch:** `cursor/nfl-ui-overhaul-0793` → `deploy-vercel`  
**Verify pass:** `cursor/nfl-overhaul-prod-gaps-8330` → `deploy-vercel`  
**Positioning:** “I give the info, you make the picks.” Research desk, not picks-selling.

Production base: https://www.kosedge.com

---

## Completion matrix (24 surfaces)

| # | Surface | Status | Live URL | Notes |
|---|---------|--------|----------|-------|
| 1 | Global header + NFL subnav | **DONE** | all `/pro/nfl/*`, `/edge-board/nfl`, `/odds/nfl`, model health/CLV | `NflProShell` / `NflProHeader` |
| 2 | NFL Overview prototype | **DONE** | [/pro/nfl/overview](https://www.kosedge.com/pro/nfl/overview) | At a Glance, workflow, elevated Weekly Slate; removed Article Highlights wall |
| 3 | Edge Board | **DONE** | [/edge-board/nfl](https://www.kosedge.com/edge-board/nfl) | Shared chrome; research tone; Overview/Slate CTAs |
| 4 | KEI Lines | **DONE** | [/pro/nfl/fair-lines](https://www.kosedge.com/pro/nfl/fair-lines) | Week labels; ET kickoffs; model vs market copy |
| 5 | Edges | **DONE** | [/pro/nfl/edges](https://www.kosedge.com/pro/nfl/edges) | Softened Side→Lean; hid Confidence; Week N · YYYY labels |
| 6 | Props (tabbed) | **DONE** | [/pro/nfl/props](https://www.kosedge.com/pro/nfl/props) | Props Board + Weekly Fantasy tab; meta stats removed; PLAY default |
| 7 | Power Ratings | **DONE** | [/pro/power-ratings/nfl](https://www.kosedge.com/pro/power-ratings/nfl) | Rank/Team/Rating/Off/Def/WeeklyΔ/RankΔ/Record; At a Glance; history bundles |
| 8 | Team Research Hub | **DONE** | [/pro/nfl/teams](https://www.kosedge.com/pro/nfl/teams) | Instant filters; Overview + Edge Board links |
| 9 | Team pages (routing fix) | **PARTIAL → fixed** | [/pro/nfl/teams/KC/overview](https://www.kosedge.com/pro/nfl/teams/KC/overview) | KC/DAL path OK on prod; verify pass adds ESPN/legacy aliases (WSH→WAS, JAC→JAX, LA→LAR) + 404 for unknown codes instead of silent BUF |
| 10 | Prediction Markets | **DONE** | [/pro/prediction-market](https://www.kosedge.com/pro/prediction-market) | Week + ML/Total; Kalshi/Polymarket/Novig placeholders |
| 11 | Execution Monitor | **DONE** | [/pro/nfl/execution](https://www.kosedge.com/pro/nfl/execution) | Dispersion, Price Quality, Timing, Book Snapshot |
| 12 | Futures | **DONE** | [/pro/nfl/projections](https://www.kosedge.com/pro/nfl/projections) | Team \| Player tabs; instant filters; research copy |
| 13 | Standings | **DONE** | [/pro/nfl/standings](https://www.kosedge.com/pro/nfl/standings) | Division/Conference/League; KEI proj wins + playoff prob |
| 14 | Depth Charts | **DONE** | [/pro/nfl/depth-charts](https://www.kosedge.com/pro/nfl/depth-charts) | Cleaner columns; source/noisy zeros removed |
| 15 | Injuries | **DONE** | [/pro/nfl/injuries](https://www.kosedge.com/pro/nfl/injuries) | Team-first intel + ESPN headlines; Eastern times (EDT) |
| 16 | Fantasy Draft Board | **DONE** | [/pro/nfl/fantasy](https://www.kosedge.com/pro/nfl/fantasy) | Existing VOR board; inherits NFL shell |
| 17 | Weekly Fantasy | **DONE** | [/pro/nfl/weekly-fantasy](https://www.kosedge.com/pro/nfl/weekly-fantasy) | Real page (no redirect); scoring + pos filters |
| 18 | DFS | **DONE** | [/pro/nfl/dfs](https://www.kosedge.com/pro/nfl/dfs) | DK/FD toggle; salary/own placeholders; model proj live |
| 19 | Model Health & Governance | **PARTIAL → fixed** | [/pro/model-transparency](https://www.kosedge.com/pro/model-transparency), [/pro/clv-tracker](https://www.kosedge.com/pro/clv-tracker) | Verify pass wraps both in `NflProShell` (logo header + Overview/Edge Board) |
| 20 | Weekly Slate | **PARTIAL → fixed** | [/pro/nfl/slate/today](https://www.kosedge.com/pro/nfl/slate/today) | Cards loaded; verify pass wires Matchup brief + team desk jumps from `matchupHref` |
| 21 | Matchups (game pages) | **DONE** | `/pro/nfl/matchups/[date]/[slug]` | Writer preview slot, Model vs Market, jumps to Edge Board / teams / props |
| 22 | Team Previews | **DONE** | [/pro/nfl/previews](https://www.kosedge.com/pro/nfl/previews) | At a Glance; AFC/NFC jumps; author + Read preview |
| 23 | Player Previews | **DONE** | [/pro/nfl/player-previews](https://www.kosedge.com/pro/nfl/player-previews) | Dedicated index (not Awards redirect) |
| 24 | Awards | **DONE** | [/pro/nfl/awards](https://www.kosedge.com/pro/nfl/awards) | Existing tabs; inherits NFL shell |
| 25 | Wall Chart | **DONE** | [/wall-chart/nfl-2026](https://www.kosedge.com/wall-chart/nfl-2026) | Interactive + print 24×18; intentionally omits desk chrome |
| 26 | Compare Odds | **DONE** | [/odds/nfl](https://www.kosedge.com/odds/nfl) | NFL chrome; Overview/KEI/Edge Board links |

---

## Global rules checklist

| Rule | Status |
|------|--------|
| Consistent logo header on NFL pages | DONE (CLV + Model Health wrapped in verify pass) |
| Nav to Overview + Edge Board on subpages | DONE |
| Instant-apply filters (no Apply Filters) | DONE (`TeamIntelFilterBar` client instant; no Apply Filters in HTML) |
| Remove sausage-making meta on Props | DONE |
| Times in ET | DONE (`formatKickoff` + injury headlines in EDT/ET) |
| Week labels “Week N · YYYY” | DONE on Edges / KEI / Execution / Prediction Markets |
| Dark theme consistent | DONE (Kos gold/black tokens) |
| Research-oriented tone | DONE across touched copy |

---

## Critical defect

**Team routing → always Bills:** Fixed for directory codes (KC/DAL).  
**Verify gap:** ESPN/legacy aliases (`WSH`, `JAC`, `LA`, …) still fell through to BUF and rendered Bills under the wrong URL. Fixed by alias normalization + canonical redirect + `notFound()` for unknown codes.

---

## Production verify (2026-07-31)

| Check | Result |
|-------|--------|
| `origin/deploy-vercel` includes PR #27 (`005ec21`) | PASS |
| Prod deploy SHA | `338a7109fe63c7ddf63f06e570d8791a144374a3` (verify fixes; Ready) |
| Vercel production branch | `deploy-vercel` |
| www.kosedge.com Ready | PASS |
| KC / DAL team pages | PASS (Chiefs / Cowboys) |
| WSH / JAC aliases (post-fix) | PASS → WAS Commanders / JAX Jaguars |
| Unknown team codes | PASS → 404 (no silent BUF) |
| CLV / Model Health shell | PASS (NflProShell + Overview/Edge Board) |
| Slate matchup links | PASS (`matchupHref` wired; 98 links on today slate) |

---

## Follow-ons (not blocking this pass)

1. Wire DK/FD salary + ownership feeds into DFS (placeholders honest today).  
2. Kalshi / Polymarket / Novig venue APIs into Prediction Markets.  
3. Enrich matchup brief with live fair-line/odds join beyond template slots.  
4. Futures page Team \| Player tab chrome polish on `/pro/nfl/projections`.  
5. ~~Wrap model-transparency / clv-tracker with `NflProHeader`~~ — done in verify pass.
