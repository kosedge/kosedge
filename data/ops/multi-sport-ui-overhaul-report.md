# Multi-Sport UI Overhaul — Progress Report

**Branch:** `cursor/multi-sport-densify-37e9` → `deploy-vercel`  
**Last updated:** 2026-07-31  
**Philosophy:** “I give the info, you make the picks.”  
**PR #33 (merged):** https://github.com/kosedge/kosedge/pull/33 — merge SHA `c03d3e40ae2d2d233a27214b0716aec39e853ddf`  
**Prod deploy:** Vercel Production `kosedge-3bpoiiiy3` (GitHub deployment id `5695853078`)

## Slice 1–3 shipped — Shared SportProShell + Overview pattern

See PR #33 history. Foundation: `SportProShell` / `SportProHeader`, per-sport nav IA, Overview/Edge Board/Odds consistency, college Tempo, NHL Goalie Desk, MLB desk chrome, mobile stacked cards.

## Slice 4 shipped — Densify with real feeds (no fakes)

### Data wiring
| Item | Status | Notes |
|------|--------|-------|
| Direct edge-board assemble (no self-HTTP) | DONE | `loadAssembledEdgeBoardRows` for pages + `getTonightGames` |
| Odds quota fallback snapshots | DONE | `edge_board_fallback_{cfb,nhl,mlb}.json` when Odds API empty |
| MLB KEI from model-service fair-lines | DONE | `resolveKeiGames("mlb")` + board merge |
| Fair Lines market context (no KEI) | DONE | Labeled “Market lines on the board” — never as fair prices |
| Edges slate context | DONE | Quantified seps when present; market slate otherwise |
| MLB Props research densify | DONE | Fair-line game slate + stake gate honesty |
| NCAAM Power Ratings | DONE | `power_ratings_ncaam.json` (365 teams) live |
| NCAAM Fair Lines KEI | DONE | `kei_lines_ncaam.json` |

### Completion matrix (sport × page)

Legend: **DONE** · **PARTIAL** · **BLOCKED** (feed missing)

| Page | NFL | NCAAM | CFB | NBA | MLB | NHL | WNBA |
|------|-----|-------|-----|-----|-----|-----|------|
| Overview | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Edge Board | DONE | DONE | DONE† | PARTIAL | DONE† | DONE† | PARTIAL |
| KEI / Fair Lines | DONE | DONE | PARTIAL‡ | PARTIAL‡ | DONE | PARTIAL‡ | PARTIAL‡ |
| Edges | DONE | PARTIAL | PARTIAL‡ | PARTIAL‡ | DONE | PARTIAL‡ | PARTIAL‡ |
| Compare Odds | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Power Ratings | DONE | DONE | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| Team Research Hub | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Weekly/Daily Slate | DONE | DONE | DONE† | PARTIAL | DONE† | DONE† | PARTIAL |
| Execution Monitor | DONE | DONE | DONE† | PARTIAL | DONE† | DONE† | PARTIAL |
| Model / CLV | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Sport desk (Tempo/Props/RL/Goalie) | DONE* | DONE | DONE† | PARTIAL | DONE | DONE† | PARTIAL |
| Props | DONE | n/a | n/a | PARTIAL | PARTIAL§ | PARTIAL | PARTIAL |

\*NFL desk = Props/Fantasy/Wall Chart (kept).  
†Board rows from Odds live pull **or** shipped last-known snapshot when Odds API is out of credits.  
‡Fair Lines / Edges show market board context; KEI model board still pending (not faked).  
§MLB props: game slate from fair-lines; player-prop stake gate remains off.

### Remaining PARTIAL / BLOCKED

| Gap | Why |
|-----|-----|
| NBA / WNBA Edge Board + Slate density | No Odds snapshot + Odds API out of credits; no model-service fair-lines |
| CFB / NHL / NBA / WNBA KEI Fair Lines | No `kei_lines_*.json` and no model-service board (except MLB/NFL/NCAAM) |
| Non-NFL Edges quantified seps | Need KEI + market join; market slate shown honestly until then |
| NBA / WNBA / NHL Props | No validated props feed on model-service |
| Power Ratings CFB/NBA/MLB/NHL/WNBA | No `power_ratings_*.json` / engine export yet |
| NHL Goalie starter names | Confirmation feed not connected — slate + totals only |
| Tempo dedicated pace/havoc columns | Board totals used until college tempo feed join |

### Live smoke (www.kosedge.com) — post PR #33 merge

| Route | HTTP | SportProShell / logo / nav |
|-------|------|----------------------------|
| `/pro/nfl/overview` | 200 | At a Glance, Workflow, Wall Chart (NFL-only), logo |
| `/pro/ncaam/overview` | 200 | At a Glance, Workflow, Tempo, logo |
| `/pro/cfb/overview` | 200 | At a Glance, Workflow, logo |
| `/pro/nba/overview` | 200 | At a Glance, Workflow, logo |
| `/pro/mlb/overview` | 200 | At a Glance, Workflow, Run Line, logo |
| `/pro/nhl/overview` | 200 | At a Glance, Workflow, logo |
| `/pro/wnba/overview` | 200 | At a Glance, Workflow, logo |
| `/edge-board/{sport}` ×7 | 200 | Overview + Edge Board nav; not SSO-gated |
| `/pro/{sport}/fair-lines` ×7 | 200 | NCAAM KEI live; NBA/CFB honest “Model board pending” |

### Preserved
- DeploymentRecovery, BootShell, logo paths, upstream timeouts  
- NFL-only Wall Chart / Fantasy / DFS / Awards / Depth Charts / Futures / Prediction Markets

### Next slices
1. Replenish Odds API credits / raise tier — restores live Open/Best for all sports  
2. Export KEI boards for CFB/NBA/NHL/WNBA when engines exist  
3. Props boards for NBA/WNBA/MLB when feeds clear validation  
4. Power-ratings exports for non-NCAAM/non-NFL  
5. Goalie confirmation feed join  
6. Refresh edge_board_fallback_*.json on a cadence while Odds quota is tight
