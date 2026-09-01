# NHL Chapter 0 — discovery audit

**Phase:** Audit only. No pack. No filling the blank KEI.  
**As of:** `2026-09-01`  
**Brief:** [`docs/NHL_CH0_DISCOVERY_BRIEF.md`](./NHL_CH0_DISCOVERY_BRIEF.md)  
**Plan:** [`artifacts/NHL_ENTERPRISE_PLAN.md`](../artifacts/NHL_ENTERPRISE_PLAN.md)  
**Leave alone:** NBA · WNBA · CFB · NFL

Every row is a **path** or **`missing`**. Do not invent Odds keys, ratings, or KEINHL numbers.

Hockey is not NBA with skates. Same desk contract. Different physics.

---

## Decision — next PR

| Pick  | Condition                       | Result                                           |
| ----- | ------------------------------- | ------------------------------------------------ |
| A     | Market + stats exist            | → Chapter 1 NHL prior (own shrink, own filename) |
| **B** | No stats path                   | → **fetcher, then Ch1**                          |
| C     | A hidden KEINHL leftover exists | → document, don’t blend                          |

### **Pick: B**

- `icehockey_nhl` is already mapped and live for mainlines (puck line / ML / totals) on `/edge-board/nhl` and `/odds/nhl`.
- **No** `nhl_*` model-service engine, **no** schedule pack, **no** 2025–26 team tables, **no** multi-year skater/goalie packs on disk.
- Therefore: **stand up an NHL stats fetcher first**, then Chapter 1 team prior with **own shrink + own filename**. Still **no** props, **no** KEI emit, **no** tags.

**Not A:** markets exist; stats/engine packs do not (contrast NBA `nba_data.py` / WNBA `wnba_data.py` + season engines).  
**C hygiene (not primary):** `KEINHL` is **brand-only** in `kei-brand.ts`. Edge Board deliberately returns `[]` from `resolveKeiGames("nhl")`. There is **no** leftover printed fair line to blend — blank on purpose. Document; do not invent a number to fill it.

---

## 0. Board KEI honesty (read first)

| Surface               | What prints                  | Source                                                     |
| --------------------- | ---------------------------- | ---------------------------------------------------------- |
| KEI column            | **empty** (honest)           | `resolveKeiGames("nhl")` → early `return []`               |
| Edge / tags           | **empty**                    | `sportIsMarketsOnlyEdgeBoard("nhl") === true`              |
| Live / fallback books | Spreads (puck line) + totals | Odds API `icehockey_nhl` or `edge_board_fallback_nhl.json` |

Code contract:

- `apps/web/lib/resolve-kei-lines.ts` — “Markets-only: NHL has no KEI source yet.”
- `apps/web/lib/edge-board-kei-availability.ts` — NHL is the only markets-only Edge Board sport.
- `apps/web/lib/build-edge-board-rows.ts` — Odds/fallback only; do not invent KEI.
- Writer / research standards — **NEVER mint** KEINHL.

**Ch0–Ch3 must not mint `kei_lines_nhl.json` or fair-line KEI.** Ch4 is the first authorized emit.

---

## 1. Product surfaces

Static `apps/web/app/(pro)/pro/nhl/` tree = **`missing`**. Desk pages are shared `[sport]` routes (plus Goalie Desk).

| Surface             | Path                                                                                 | Status                  | Notes                                                                               |
| ------------------- | ------------------------------------------------------------------------------------ | ----------------------- | ----------------------------------------------------------------------------------- |
| Edge Board          | `/edge-board/nhl` → `apps/web/app/edge-board/[sport]/page.tsx`                       | **live (markets-only)** | Odds or fallback; KEI/edge/tags empty                                               |
| Edge Board fallback | `apps/web/data/processed/edge_board_fallback_nhl.json`                               | **exists**              | `capturedAt=2026-07-31T18:12:23Z`; `eventCount=31`; 62 rows                         |
| Odds compare        | `/odds/nhl` → `apps/web/app/odds/[sport]/page.tsx`                                   | **live**                | `spreads,h2h,totals` via `icehockey_nhl`                                            |
| Overview            | `/pro/nhl/overview` → `…/[sport]/overview/page.tsx`                                  | **live hub**            | Tonight scroller from board; desk cards Fair Lines → Edges → Goalie Desk            |
| Fair Lines          | `/pro/nhl/fair-lines`                                                                | **shell**               | Copy: model pending. Market open/best when present — **not** KEI                    |
| Edges               | `/pro/nhl/edges`                                                                     | **shell**               | Board-derived only; without KEI → honest empty edges                                |
| Goalie Desk         | `/pro/nhl/goalies` → `…/[sport]/goalies/page.tsx` + `lib/nhl-goalie-confirmation.ts` | **partial live**        | ESPN scoreboard `probables`; Pending when names absent; no model sensitivity        |
| Props               | `/pro/nhl/props` → `…/[sport]/props/page.tsx`                                        | **placeholder**         | Copy only (“once shot and save feeds clear”); **no** props board API                |
| Fantasy             | `/pro/nhl/fantasy`                                                                   | **missing**             | NBA/WNBA have `pro/{sport}/fantasy/page.tsx`; NHL does not. Nav has no Fantasy link |
| Teams               | `/pro/nhl/teams`                                                                     | **shell**               | 32 clubs in `directories-pro.ts` (`NHL_TEAM_DIRECTORY`); sections mostly `pending`  |
| Injuries            | `/pro/nhl/injuries`                                                                  | **partial**             | RotoWire RSS (`sport-injury-news.ts`); designation table pending                    |
| Standings           | `/pro/nhl/standings` (nav links)                                                     | **missing\***           | `[sport]/standings/page.tsx` → `notFound()` unless `nfl`                            |
| Stats               | `/pro/nhl/stats`                                                                     | **missing\***           | Same NFL-only gate                                                                  |
| KEI Lines hub       | `/pro/kei-lines/nhl`                                                                 | **empty-honest**        | No `kei_lines_nhl.json`; markets-only copy                                          |
| Power Ratings       | `/pro/power-ratings/nhl`                                                             | **shell**               | No `power_ratings_nhl.json`                                                         |
| Slate / matchups    | `/pro/nhl/slate/...`, matchups                                                       | **live chrome**         | Market context; no model drivers                                                    |

\*Route file exists under `[sport]` but hard-404s for NHL.

### Desk IA (paths)

| File                             | NHL role                                                              |
| -------------------------------- | --------------------------------------------------------------------- |
| `apps/web/lib/sport-pro-nav.ts`  | Goalie Desk + Limited Props; Injuries; Standings (404)                |
| `apps/web/lib/pro-sport-desk.ts` | Path: Fair Lines → Edges → Goalie Desk                                |
| `apps/web/lib/sport-overview.ts` | Glance: Model vs Market, Goalie Desk, Key Edges, Team Research        |
| `apps/web/lib/sports.ts`         | `supportsPropsFantasy: true` for NHL (UI flag only — no fantasy page) |
| `apps/web/lib/kei-brand.ts`      | Column label `KEINHL` — **brand only**                                |

Ops evidence: `data/ops/multi-sport-ui-overhaul-report.md`, `data/ops/edge-board-population-status-2026-08-02.md`.

---

## 2. Market — Odds / `icehockey_nhl`

| Question                                   | Finding                                                                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------ |
| Does Odds client call `icehockey_nhl`?     | **Yes** — `apps/web/lib/odds-api.ts` `SPORT_KEY_MAP.nhl = "icehockey_nhl"`           |
| Edge Board live markets                    | `spreads,totals` (puck line + totals)                                                |
| Odds compare markets                       | `spreads,h2h,totals`                                                                 |
| Trusted books                              | Shared `ALLOWED_BOOKS` (no NHL-only allowlist)                                       |
| Live web fetch of player props?            | **No** — web Odds client does not request NHL player prop markets for tonight boards |
| Training / warehouse prop keys **in code** | See table below                                                                      |

### Prop keys named in training pull (`scripts/odds/enterprise_training_pull.py`)

| Odds API key           | Stored    |
| ---------------------- | --------- |
| `player_points`        | `pts`     |
| `player_goals`         | `goals`   |
| `player_assists`       | `assists` |
| `player_shots_on_goal` | `sog`     |

**Not named in code (do not invent in Ch0–Ch1):** goalie saves, goalie wins, blocked shots, hits, PPP, etc.

### Scripts

| File                                         | NHL role                                   |
| -------------------------------------------- | ------------------------------------------ |
| `scripts/odds/enterprise_training_pull.py`   | Full `SportPlan` for NHL (`icehockey_nhl`) |
| `scripts/odds/persist_mainline_odds.py`      | Maps `icehockey_nhl` → league NHL          |
| `scripts/odds/build_edge_board_fallbacks.py` | Builds `edge_board_fallback_nhl.json`      |
| `scripts/odds/verify_training_pull.py`       | Lists `("nhl", "icehockey_nhl")`           |

### Warehouse snapshot honesty

`data/ops/odds-enterprise-training-pull/summary.json` inventory shows `nhl.mainline_games: 0`, `prop_rows: 0` for that file’s DB view. Checkpoint lists NHL in the pull order — treat as “pull wired,” **not** proof of local multi-year prop warehouse rows in this workspace. Do not invent return rates; Ch0 only registers the keys coded above.

---

## 3. Leftovers — `nhl_*` / KEINHL / model-service

| Area                                    | Status          | Evidence                                                                         |
| --------------------------------------- | --------------- | -------------------------------------------------------------------------------- |
| `nhl_*.py` modules                      | **missing**     | No matches under `services/model-service/src/services/`                          |
| `nhl_season_engine/`                    | **missing**     | Contrast: `nba_season_engine/`, `wnba_season_engine/`                            |
| `scripts/nhl/`                          | **missing**     | —                                                                                |
| Model-service routes / Celery NHL tasks | **missing**     | Zero NHL/icehockey route or task hits                                            |
| SQL / migrations `nhl_*`                | **missing**     | —                                                                                |
| `KEINHL` computation / JSON             | **missing**     | Brand label only (`kei-brand.ts`)                                                |
| Writer mint ban                         | **live policy** | `style-bible.md`, `research-standards.md`, `content/writers/desk-2026/README.md` |

**C note:** Unlike WNBA’s leftover printed board KEI (stale poss-sim rows), NHL has **no printed house numbers**. Path **C is not the primary pick** — there is nothing to blend. Keep markets-only until Ch4.

---

## 4. Data paths — schedule / tables / starters

| Asset                             | Status                           | Evidence                                                                                                                                                            |
| --------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026–27 **84-game** schedule pack | **missing**                      | No `*nhl*schedule*` / prior packs. 84-game cited in writer copy only                                                                                                |
| 2025–26 team rate tables (repo)   | **missing**                      | —                                                                                                                                                                   |
| Multi-year skater tables          | **missing**                      | —                                                                                                                                                                   |
| Multi-year goalie tables          | **missing**                      | —                                                                                                                                                                   |
| Season-engine data packs          | **missing**                      | No `…/nhl_*/data/`                                                                                                                                                  |
| `data/` NHL artifacts             | **missing** (ops/odds meta only) | Odds pull checkpoint/summary                                                                                                                                        |
| `apps/web/data` NHL               | **fallback JSON only**           | `edge_board_fallback_nhl.json`                                                                                                                                      |
| Starter ingest — ESPN             | **exists (code)**                | `apps/web/lib/nhl-goalie-confirmation.ts` → ESPN NHL scoreboard `probables`                                                                                         |
| SportsData NHL endpoints          | **catalog only**                 | `apps/web/data/raw/sportsdata_replay_endpoints.json`: CurrentSeason, GamesByDate, GameOddsByDate, PBP, BoxScore, ScoreSummary — **no** StartingGoalie ingest module |
| Camps / opening night (calendar)  | **documented in plan**           | Camps ~Sep 16 · Preseason Sep 19–26 · Opening night **Sep 29**                                                                                                      |

**Bottom line:** no real NHL stats/projection tables in `data/`, model-service, or `apps/web/data/` beyond odds fallback + ESPN goalie confirmation code.

---

## 5. Register only (this chapter — do not code)

| Name                      | Value                                          | Notes                                              |
| ------------------------- | ---------------------------------------------- | -------------------------------------------------- |
| `ODDS_SPORT_KEY`          | `icehockey_nhl`                                | Already live in `odds-api.ts`                      |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50`                           | Ch2 on players — season labels TBD at fetcher time |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                                            | Ch6 — between NBA 8 and WNBA 4                     |
| `STARTER_GATE`            | unknown → **no goalie PLAY**; total sized down | Closest live analog: Goalie Desk ESPN confirmation |

Do **not** register basketball `MINUTE_GRID_SUM` / home coeffs for NHL. TOI + PP1/PP2 are Ch2 physics.

---

## 6. Explicit anti-patterns (audit confirmation)

| Anti-pattern                      | Status in repo today                                  |
| --------------------------------- | ----------------------------------------------------- |
| Invent KEINHL to fill Edge Board  | **Blocked** by `resolveKeiGames` + markets-only flag  |
| Props from puck-line residue      | **N/A** (no props engine) — forbidden going forward   |
| Blend MoneyPuck / NST / EH as SoT | **Not present** — keep it that way                    |
| Port NBA `+2.0` / WNBA `+1.5`     | **Not present**                                       |
| Goalie PLAY with unknown starter  | **N/A** (no tags) — `STARTER_GATE` registered for Ch6 |
| Touch NBA / WNBA / CFB / NFL      | **This PR does not**                                  |

---

## Decision matrix (recap)

| Pick  | Condition                                      | NHL                                    |
| ----- | ---------------------------------------------- | -------------------------------------- |
| A     | Market + stats exist → Ch1 prior               | Markets **yes**; stats **no**          |
| **B** | No stats → fetcher, then Ch1                   | **← written pick**                     |
| C     | Hidden KEINHL leftover → document, don’t blend | Brand-only; blank board — hygiene only |

### Why B

Odds + UI chrome are ready. Next work is a **stats fetcher** (schedule + prior-year team rates + multi-year skater/goalie grain), then Ch1 team prior with **own shrink and own filename** — still no props desk, no Edge Board KEI emit.

### Forbidden for next PR after merge

Invent KEI · props PLAY/LEAN · fake goalie names · blend nonexistent leftover KEINHL · copy NBA/WNBA shrink/filenames into an NHL engine that does not exist yet · edit NBA/WNBA/CFB/NFL.
