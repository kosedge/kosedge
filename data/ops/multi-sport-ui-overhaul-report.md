# Multi-Sport UI Overhaul — Progress Report

**Branch:** `cursor/multi-sport-odds-restore-f5a4` → `deploy-vercel`  
**Last updated:** 2026-07-31  
**Philosophy:** “I give the info, you make the picks.”  
**PR #33 (merged):** https://github.com/kosedge/kosedge/pull/33 — merge SHA `c03d3e40ae2d2d233a27214b0716aec39e853ddf` → dpl `dpl_2mq4inYonuiinK8W3bBqLt49svp9`  
**PR #34 (merged):** https://github.com/kosedge/kosedge/pull/34 — merge SHA `0c0abf253f052ccd5f22ca6703eaa0df08de2a50` → dpl `dpl_Hr4SgQw8ieTekmvgxPpwop3x6Fes`  
**PR #35 (merged):** https://github.com/kosedge/kosedge/pull/35 — docs dpl record  
**Odds key rotation redeploy (env-only):** `dpl_5ethEXS86u6xTsid9bfG3wQdG7sd` (www — post ODDS_API_KEY restore)

## Slice 1–3 shipped — Shared SportProShell + Overview pattern

See PR #33 history. Foundation: `SportProShell` / `SportProHeader`, per-sport nav IA, Overview/Edge Board/Odds consistency, college Tempo, NHL Goalie Desk, MLB desk chrome, mobile stacked cards.

## Slice 4 shipped — Densify with real feeds (no fakes)

### Data wiring
| Item | Status | Notes |
|------|--------|-------|
| Direct edge-board assemble (no self-HTTP) | DONE | `loadAssembledEdgeBoardRows` for pages + `getTonightGames` |
| Odds API production key | DONE | Rotated Production/Preview to high-volume key (~2.99M credits). Free-tier backup exhausted (~1 left). |
| Odds quota fallback snapshots | DONE | Refreshed `edge_board_fallback_{cfb,nhl,mlb,wnba}.json` from live pull; NBA empty (offseason) |
| MLB KEI from model-service fair-lines | DONE | `resolveKeiGames("mlb")` + board merge |
| Fair Lines market context (no KEI) | DONE | Labeled “Market lines on the board” — never as fair prices |
| Edges slate context | DONE | Quantified seps when present; market slate otherwise |
| MLB Props research densify | DONE | Fair-line game slate + stake gate honesty |
| WNBA Props / slate densify | DONE | Live Odds slate context; player props still gated |
| NCAAM Power Ratings | DONE | `power_ratings_ncaam.json` (365 teams) live |
| NCAAM Fair Lines KEI | DONE | `kei_lines_ncaam.json` |
| NHL Goalie confirmation source | PARTIAL | ESPN scoreboard wired (`nhl-goalie-confirmation.ts`); no starter names posted yet → honest Pending |

### Completion matrix (sport × page)

Legend: **DONE** · **PARTIAL** · **BLOCKED** (feed missing)

| Page | NFL | NCAAM | CFB | NBA | MLB | NHL | WNBA |
|------|-----|-------|-----|-----|-----|-----|------|
| Overview | DONE | DONE | DONE | DONE† | DONE | DONE | DONE |
| Edge Board | DONE | DONE | DONE | DONE† | DONE | DONE | DONE |
| KEI / Fair Lines | DONE | DONE | PARTIAL‡ | PARTIAL‡ | DONE | PARTIAL‡ | PARTIAL‡ |
| Edges | DONE | PARTIAL | PARTIAL‡ | PARTIAL‡ | DONE | PARTIAL‡ | PARTIAL‡ |
| Compare Odds | DONE | DONE | DONE | DONE† | DONE | DONE | DONE |
| Power Ratings | DONE | DONE | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| Team Research Hub | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Weekly/Daily Slate | DONE | DONE | DONE | DONE† | DONE | DONE | DONE |
| Execution Monitor | DONE | DONE | DONE | DONE† | DONE | DONE | DONE |
| Model / CLV | DONE | DONE | DONE | DONE | DONE | DONE | DONE |
| Sport desk (Tempo/Props/RL/Goalie) | DONE* | DONE | DONE | PARTIAL | DONE | DONE§ | PARTIAL |
| Props | DONE | n/a | n/a | PARTIAL | PARTIAL¶ | PARTIAL | PARTIAL |

\*NFL desk = Props/Fantasy/Wall Chart (kept).  
†NBA: Odds API `basketball_nba` returns **0 events** (offseason). Honest empty — not a key failure.  
‡Fair Lines / Edges show market board context; KEI model board still pending (not faked).  
§Goalie Desk: ESPN connected; starter names Pending until ESPN posts probables.  
¶MLB props: game slate from fair-lines; player-prop stake gate remains off.

### Remaining PARTIAL / BLOCKED (true blockers)

| Gap | Why |
|-----|-----|
| CFB / NHL / NBA / WNBA KEI Fair Lines | No `kei_lines_*.json` and no model-service board (only MLB/NFL/NCAAM engines expose fair-lines) |
| Non-NFL Edges quantified seps | Need KEI + market join; market slate shown honestly until then |
| NBA / WNBA / NHL player Props boards | No validated props feed on model-service |
| Power Ratings CFB/NBA/MLB/NHL/WNBA | No `power_ratings_*.json` / engine export yet (NCAAM + NFL only) |
| NHL Goalie starter names | ESPN scoreboard wired; `probables` empty on current/preseason boards |
| Tempo dedicated pace/havoc columns | Board totals used until college tempo feed join |
| NBA live mainlines | Offseason — Odds API inactive for `basketball_nba` until board posts |

### Live smoke (www.kosedge.com) — post Odds key restore (`dpl_5ethEXS86u6xTsid9bfG3wQdG7sd`)

| Route | HTTP | Notes |
|-------|------|-------|
| `/api/odds/nba/compare` | 200 | 0 rows (offseason) |
| `/api/odds/wnba/compare` | 200 | **5 rows** (Storm @ Dream …) |
| `/api/odds/cfb/compare` | 200 | **126 rows** |
| `/api/odds/nhl/compare` | 200 | **31 rows** |
| `/api/odds/mlb/compare` | 200 | **29 rows** |
| `/api/odds/nfl/compare` | 200 | **272 rows** |
| `/pro/wnba/overview` | 200 | Slate live (Storm/Dream) |
| `/pro/nba/overview` | 200 | Honest empty (offseason) |
| `/pro/cfb/overview` | 200 | Tar Heels / slate live |
| `/pro/nhl/overview` | 200 | Panthers slate live |
| `/pro/mlb/overview` | 200 | Yankees slate live |
| `/edge-board/wnba` | 200 | Live rows |
| `/edge-board/nba` | 200 | Honest empty / No live |
| `/edge-board/cfb\|nhl\|mlb` | 200 | Live rows |
| `/pro/ncaam/fair-lines` | 200 | KEI projections on file |
| `/pro/cfb\|nhl\|wnba/fair-lines` | 200 | Market lines on the board (no fake KEI) |
| `/pro/nhl/goalies` | 200 | Slate + Confirmation pending (ESPN, no names) |
| `/pro/mlb/props` | 200 | Props gated + fair-line game slate |
| `/pro/wnba/props` | 200 | Props gated + Odds slate context |
| `/pro/power-ratings/ncaam` | 200 | 365 teams |
| `/pro/power-ratings/cfb` | 200 | Pending feed (no invented ratings) |
| `/odds/{sport}` | 200 | Compare Odds surfaces |

### Odds API ops notes
- **Working key** (Development + rotated Production/Preview): ~**2,989,500** credits remaining after restore pulls.
- Prior Production/Preview values were `sensitive`-type and effectively tied to exhausted free-tier usage (compare caches + embedded backup with ~1 credit).
- Embedded code backup key is exhausted — do not rely on it.
- Rebuild fallbacks: pull raw odds → `python scripts/odds/build_edge_board_fallbacks.py` (do not commit `odds_raw_*.json`).

### Preserved
- DeploymentRecovery, BootShell, logo paths, upstream timeouts  
- NFL-only Wall Chart / Fantasy / DFS / Awards / Depth Charts / Futures / Prediction Markets  
- No fabricated KEI / power ratings / goalie names / prop cards

### Next slices
1. Export KEI boards for CFB/NBA/NHL/WNBA when engines exist on model-service  
2. Props boards for NBA/WNBA/MLB when feeds clear validation  
3. Power-ratings exports for non-NCAAM/non-NFL  
4. Goalie names when ESPN (or enterprise) posts probables  
5. Refresh edge_board_fallback_*.json on a cadence as boards turn over  
6. NBA densify automatically when Odds API posts preseason/regular board  
