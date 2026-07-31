# Multi-Sport UI Overhaul — Progress Report

**Branch:** `cursor/multi-sport-ui-shell-a93a` → `deploy-vercel`  
**Last updated:** 2026-07-31  
**Philosophy:** “I give the info, you make the picks.”  
**PR:** https://github.com/kosedge/kosedge/pull/33

## Slice 1 shipped — Shared SportProShell + Overview pattern

### Foundation
| Item | Status | Notes |
|------|--------|-------|
| `SportProShell` / `SportProHeader` | DONE | Generalizes NflProShell across all sports |
| `lib/sport-pro-nav.ts` | DONE | Per-sport primary + tool nav; NFL-only Wall Chart/Fantasy/DFS/Awards |
| `[sport]/layout` + `mlb/layout` + `nfl/layout` | DONE | Consistent chrome |
| Edge Board header+nav all sports | DONE | Overview + Slate + Odds CTAs; ET callout |
| Odds Compare header+nav all sports | DONE | Mobile stacked cards + desktop table |
| Edge Board mobile stacked cards | DONE | Replaced wide mobile table |
| Sport Overview (NFL pattern) | DONE | At a Glance, Workflow, elevated Slate, no Article Highlights wall |
| College props omitted | DONE | No props section/nav; `/props` redirects to Tempo |
| Edges desk (generic) | DONE | Board-derived separations; honest empty state |
| Tempo desk (NCAAM/CFB) | DONE | Tempo/Havoc research shell |
| Goalie Desk (NHL) | DONE | Confirmation-framed shell |
| Power Ratings shell (non-NFL) | DONE | SportProShell wrap |
| KEI Lines sport pages | DONE | SportProShell wrap |

### Completion matrix (sport × page)

Legend: **DONE** · **PARTIAL** · **BLOCKED** (feed missing)

| Page | NFL | NCAAM | CFB | NBA | MLB | NHL | WNBA |
|------|-----|-------|-----|-----|-----|-----|------|
| Overview | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Edge Board | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| KEI / Fair Lines | DONE | DONE* | PARTIAL | PARTIAL | DONE | PARTIAL | PARTIAL |
| Edges | DONE | PARTIAL | PARTIAL | PARTIAL | DONE | PARTIAL | PARTIAL |
| Compare Odds | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Power Ratings | DONE | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Team Research Hub | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Weekly/Daily Slate | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Execution Monitor | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Model / CLV | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Sport desk (Tempo/Props/RL/Goalie) | DONE* | DONE | DONE | PARTIAL | DONE | DONE | PARTIAL |

\*NFL desk = Props/Fantasy/Wall Chart (kept).  
\*NCAAM Fair Lines = DONE when `kei_lines_ncaam.json` is present (wired in slice 2).  
PARTIAL elsewhere = honest shells / board-derived metrics; full model boards pending feed join (not faked).

## Slice 2 shipped — Slate / Execution / Teams / Fair Lines data

- Slate pages use live `getTonightGames` (no fake Away/Home placeholders)
- Execution Monitor for all sports (NFL fair-lines diagnostic + board-derived for others)
- Team Research detail: Overview + Edge Board nav, touch targets, sport desk links
- Fair Lines surfaces KEI JSON when available (NCAAM live file)
- Mobile stacked cards on slate/execution/fair-lines

## Slice 3 shipped — MLB desk chrome + tracking + mobile

- MLB Fair Lines / Edges headers match research-desk pattern (Overview + Edge Board)
- Removed “Actionable” picks energy from MLB Edges title
- MLB Fair Lines + Edges: mobile stacked cards
- Non-NFL Tracking uses SportHubShell with honest CLV-pending state

### Live URLs (www.kosedge.com — after deploy)

- Overview: `/pro/{sport}/overview`
- Edge Board: `/edge-board/{sport}`
- Fair Lines: `/pro/{sport}/fair-lines` (MLB/NFL dedicated)
- Edges: `/pro/{sport}/edges` (MLB/NFL dedicated)
- Tempo: `/pro/ncaam/tempo`, `/pro/cfb/tempo`
- Goalie Desk: `/pro/nhl/goalies`
- Teams: `/pro/{sport}/teams`
- Slate: `/pro/{sport}/slate/today`
- Odds: `/odds/{sport}`
- Power: `/pro/power-ratings/{sport}`
- KEI: `/pro/kei-lines/{sport}`

### Local smoke (127.0.0.1:3000) — 2026-07-31

All sports × Overview / Edge Board / Fair Lines / Edges / Teams / Slate / Odds / Power Ratings → **HTTP 200**, logo present, Overview + Edge Board nav present, no Application errors.

| Check | Result |
|-------|--------|
| NBA Overview At a Glance / Workflow | Present; no Article Highlights; no Wall Chart |
| NFL Overview Wall Chart | Present (NFL-only preserved) |
| NCAAM Fair Lines KEI file | “KEI projections on file” (38 games) |
| College `/props` | Redirects to `/tempo` (NEXT_REDIRECT 307) |
| NBA `/tempo` | 404 (college-only desk) |
| NHL Goalie Desk | 200 |
| Sport hub chips on Edge Board | CBB CFB MLB NBA NFL NHL WNBA |

Vercel preview for PR #33 is SSO-gated; production URLs land after merge to `deploy-vercel`.

### Next slices
1. Merge PR #33 → `deploy-vercel` when ready  
2. Wire remaining Fair Lines/Edges when model boards exist (NBA/NHL/WNBA/CFB)  
3. Props densify NBA/WNBA/MLB where feeds support  
4. Power ratings densify non-NFL  
5. Final www + mobile viewport smoke on production

### Preserved
- DeploymentRecovery, BootShell, logo paths, upstream timeouts  
- NFL-only Wall Chart / Fantasy / DFS / Awards / Depth Charts / Futures / Prediction Markets
