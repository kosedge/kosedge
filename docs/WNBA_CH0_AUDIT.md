# WNBA Chapter 0 — discovery audit

**Phase:** Audit only. No pack / tags / new KEI emit.  
**As of:** `2026-09-01` (midseason — regular season ends **Sep 24**; playoffs **Sep 27**)  
**Brief:** [`docs/WNBA_CH0_DISCOVERY_BRIEF.md`](./WNBA_CH0_DISCOVERY_BRIEF.md)  

Every row is a **path** or **`missing`**. Do not invent Odds keys or ratings.  
**Do not copy the NBA pack.**

---

## Decision — next PR

| Pick  | Condition                         | Result                                                |
| ----- | --------------------------------- | ----------------------------------------------------- |
| **A** | Market + stats exist              | → Chapter 1 WNBA prior (own shrink, own filename)     |
| B     | No WNBA stats path                | → fetcher, then Ch1                                   |
| C     | Board KEI is an unknown leftover  | → document, replace later, don’t blend                |

### **Pick: A**

- `basketball_wnba` is already mapped in the web Odds client; live Sep 17 markets (incl. **CON@ATL**) price on `/edge-board/wnba` and `/odds/wnba`.
- Stats / feature path exists: `wnba_data.py` + DB tables (`wnba_games_ingest`, `wnba_team_game_features`, `wnba_team_rolling_features`, `wnba_player_game_stubs`) fed by ESPN scoreboard + box proxies (data.wnba.com CDN currently 403; stats.wnba.com coded, flaky from this host).
- Therefore: **Chapter 1 WNBA team prior + own shrink + own filename** is the next PR — temporary shell. Still **no** pack in this PR, **no** tags, **no** NBA copy.

**Not B:** ingest + rolling features are live (`GET /wnba/ops/inventory`).  
**Not C:** printed board KEI is a **known** leftover (see §0) — document and **do not blend** into Ch1; provenance is `wnba-v1-poss-sim`, not unknown.

---

## 0. Board KEI honesty (read first)

Live `/edge-board/wnba` (2026-09-01) joins:

| Surface | What prints | Source |
| ------- | ----------- | ------ |
| KEI column | **LAS @ CHI +4.5** · **NY @ PHX +2.5** only | `resolveKeiGames("wnba")` → `fetchWnbaFairLines` → `/wnba/fair-lines` → model `wnba-v1-poss-sim` |
| Live books | **Connecticut Sun @ Atlanta Dream** (Sep 17) + rest of Sep 17–18 slate | Odds API `basketball_wnba` mainlines |

Fair-lines payload for “today” (count=2):

| game_id | Fair board label | ESPN truth | projected_at |
| ------- | ---------------- | ---------- | ------------ |
| `401857105` | LAS @ CHI, `fair_spread_home=4.5`, `game_date=2026-09-01` | **Final** 2026-08-01 — LV 83 @ CHI 84 | `2026-08-01T05:40:18Z` |
| `401857106` | NY @ PHX, `fair_spread_home=2.5`, `game_date=2026-09-01` | **Final** 2026-08-01 — NY 94 @ PHX 92 | `2026-08-01T05:40:19Z` |

So the numbers the desk already sees (LAS −4.5 / CHI +4.5) are **Aug 1 finals** still served as fair-lines / KEI, not the midseason CON@ATL market.  
**Ch1 must not blend these rows into a prior.** Replace via enterprise spine later; leave the research poss-sim in place (Chapter 0) — do not stand up a second engine beside it.

Props board today: `/wnba/props/board` → **0 rows** (“No WNBA prop edges materialized for this date”).

---

## 1. Product — `/pro/wnba` · `/edge-board/wnba`

Static WNBA tree is thin (`apps/web/app/(pro)/pro/wnba/` = `layout.tsx` + `fair-lines/`). Most desk pages are shared `[sport]` routes.

| Surface                | Path                                                                     | Status                 | Notes |
| ---------------------- | ------------------------------------------------------------------------ | ---------------------- | ----- |
| Overview               | `/pro/wnba/overview` → `apps/web/app/(pro)/pro/[sport]/overview/page.tsx` | **live**               | Hub; shows LAS@CHI monitoring from fair-lines join |
| Edge Board             | `/edge-board/wnba` → `apps/web/app/edge-board/[sport]/page.tsx`           | **live**               | Odds + fair-lines KEI merge; KEI only on leftover finals (§0) |
| Edge Board (pro alias) | `/pro/wnba/edge-board` or `/pro/edge-board/wnba`                         | **missing**            | Desk footer links `/edge-board/wnba` |
| Slate                  | `/pro/wnba/slate/today` → `…/[sport]/slate/[date]/page.tsx`               | **live**               | Matchup cards from Odds + KEI when joined |
| Fair Lines             | `/pro/wnba/fair-lines`                                                   | **live**               | `fetchWnbaFairLines` → `/wnba/fair-lines` |
| Props                  | `/pro/wnba/props` → `…/[sport]/props/page.tsx` + `lib/wnba-props-board.ts` | **live (research)**   | `/wnba/props/board`; stub means; **no stake tags**; empty as_of today |
| Fantasy                | `/pro/wnba/fantasy`                                                      | **missing**            | NFL + NBA Ch7 only |
| Ratings / power        | `/pro/power-ratings/wnba`                                                | **shell / missing pack** | No `power_ratings_wnba.json` |
| KEI Lines hub          | `/pro/kei-lines/wnba`                                                    | **shell**              | No `kei_lines_wnba.json`; fair-lines is the KEI surface |
| Teams                  | `/pro/wnba/teams` → `…/[sport]/teams/**`                                  | **shell**              | 15-team directory (`WNBA_TEAM_DIRECTORY`) |
| Injuries               | `/pro/wnba/injuries`                                                     | **shell / partial**    | RSS (`sport-injury-news.ts` RotoWire WNBA) |
| Standings              | `/pro/wnba/standings`                                                    | **missing\***          | `[sport]/standings` NFL-gates → `notFound()` |
| Stats / pace           | `/pro/wnba/stats`                                                        | **missing\***          | Same NFL-only `notFound()` |
| Odds compare           | `/odds/wnba`                                                             | **live**               | `odds-api.ts` → `basketball_wnba` |

\*Route file exists under `[sport]` but hard-404s for WNBA (nav still links).

### Today’s KEI from?

```text
edge-board / slate / overview
  → build-edge-board-rows.loadAssembledEdgeBoardRows("wnba")
  → resolveKeiGames("wnba")                 apps/web/lib/resolve-kei-lines.ts
  → fetchWnbaFairLines({ daysAhead: 5 })    apps/web/lib/wnba-fair-lines.ts
  → GET {MODEL_SERVICE_URL}/wnba/fair-lines
  → wnba_market_projections / wnba-v1-poss-sim
  → keiGamesFromWnbaFairLines               apps/web/lib/wnba-kei-from-fair-lines.ts
```

Fallback file: `apps/web/data/processed/edge_board_fallback_wnba.json` (Jul 31 odds snapshot — not the KEI numbers).  
File KEI pack: **`missing`** (`kei_lines_wnba.json`).

---

## 2. Market — Odds / `basketball_wnba`

| Question                                      | Finding |
| --------------------------------------------- | ------- |
| Does Odds client call `basketball_wnba`?       | **Yes** — `apps/web/lib/odds-api.ts` `SPORT_KEY_MAP.wnba = "basketball_wnba"` (spreads / totals / h2h). Also `scripts/odds/enterprise_training_pull.py` (`SportPlan` `wnba`), `persist_mainline_odds.py`, `tasks.pull_wnba_historical_odds_densify`. |
| Trusted books                                 | **Shared** `ALLOWED_BOOKS` (no WNBA-only allowlist). |
| Live web fetch of player props?               | **No** — web Odds client requests mainlines only for boards. |
| Training prop keys (in code)                  | Odds API → stored: `player_points`→`pts`, `player_rebounds`→`reb`, `player_assists`→`ast`, `player_threes`→`threes`. **No `pra`.** |
| Prop keys actually returned (warehouse)       | Checkpoint `data/ops/odds-enterprise-training-pull/checkpoint.json`: `wnba:props` **543 dates** (pulled 2026-07-27). Live DB inventory: `odds.mainline_games=274`, `odds_snapshot_rows=45148`. Agent host has **no** `ODDS_API_KEY` — cannot re-hit live event-odds props in this audit; code + checkpoint are the evidence. |
| Engine prop markets joined today              | `WNBA_PROP_MARKETS = ("pts","reb","ast","threes")` — research board; **0 rows** for as_of 2026-09-01. |

Do **not** invent additional Odds keys in Ch1 code.

---

## 3. Engine — model-service (`wnba_*` pack already exists)

This is Chapter 0 research spine — **leave running**; Ch1 is a separate prior filename, not a fork of NBA.

| Item                        | Path / status |
| --------------------------- | ------------- |
| Routes                      | `services/model-service/src/routes/wnba.py` — `/wnba/health`, `/fair-lines`, `/props/board`, `/ops/inventory`, simulations |
| Possession sim (team lines) | `wnba_possession_simulator.py` — 40-min, harmonic-mean pace, home court **2.25**, rest multipliers (not NBA situation coeffs) |
| Publish / cal               | `wnba_publish_policy.py` · `wnba_calibration.py` — mainlines **research_only** |
| Stub props (research)       | `wnba_player_prop_projection.py` · `wnba_prop_edge_policy.py` · `wnba-player-props-v1` |
| Jobs / beat                 | `wnba_jobs.py` · Celery morning ingest/context/sim + 3am `run_wnba_daily_cycle` |
| Schema / SQL                | `wnba_schema.py` · `infra/db/047_wnba_model_foundation.sql` |
| Ingest                      | `wnba_data.py` — stats.wnba.com · data.wnba.com · ESPN · optional SportsDataIO. **No NBA prior import.** |
| Shared NBA / CBB engine     | **Odds client only** (shared `odds-api.ts` sport map). Possession/prop engines are parallel `wnba_*` files — keep separate. Do not import `nba_season_engine`. |
| Ops plans                   | `data/ops/wnba-model-build-plan.md` · `data/ops/wnba-model-enterprise-grade-report.md` (Phase 0–3 research) |

### Live health / inventory (2026-09-01)

| Metric | Value |
| ------ | ----- |
| `active_model_version` | `wnba-v1-poss-sim` |
| `worker_build_id` | `wnba-poss-sim-20260801-phase3` |
| `game_minutes` / pace method | 40 / `harmonic_mean` |
| `hierarchy_wnba` | 275 |
| `wnba_games_ingest` | 913 |
| `wnba_team_game_features` | 1589 |
| `wnba_team_rolling_features` | 221 |
| `wnba_player_game_stubs` | 1494 |
| `wnba_player_prop_model_edges` | 6160 (historical materialization; **0** for today) |
| `wnba_market_projections` | 100 (includes leftover Aug-1 finals served as “slate”) |
| odds `mainline_games` | 274 |

---

## 4. 2026 slate — finals vs remaining (midseason)

Source: ESPN team schedules + day scoreboard (data.wnba.com full_schedule **403** from this host).

| Window | Finding |
| ------ | ------- |
| Last finals before break | Through **2026-08-31** — e.g. CON @ DAL Final `401857189` (Aug 31). Aug 25–30 also final. |
| Soft window | **Sep 1–16** — no ESPN RS games (midseason break). |
| Remaining RS (through Sep 24) | Resume **Sep 17** with CON @ ATL `401857190`, then ~**30** scheduled games through Sep 24 (day-walk Aug 25–Sep 30). |
| Playoffs | Brief says **Sep 27** start — ESPN schedule walk through Sep 30 shows residual Sep 25 dates; treat post–Sep 24 as postseason / buffer, not Ch1 fit. |
| Fit sample rule | **2026 games already final are not a fit sample.** Do not walkforward Ch1 on completed 2026 boxes. |

---

## 5. Stats path — 2025 + 2026-YTD team/player advanced

| Asset | Status |
| ----- | ------ |
| Ingest module | `services/model-service/src/services/wnba_data.py` |
| Team advanced (API) | **path coded** — `stats.wnba.com` `leaguedashteamstats` MeasureType=Advanced; **live probe timed out** from audit host. Not required for “path exists.” |
| Player advanced (API) | **path coded** — `leaguedashplayerstats`; same timeout. |
| data.wnba.com schedule/box | **path coded**; **403** live (known; enterprise report: ESPN-first near-term). |
| ESPN scoreboard / team schedule | **live** — used for slate truth in this audit. |
| Derived team features in DB | **live** — pace/ORtg/DRtg proxies from box (`features_from_gamelog_row`) → `wnba_team_game_features` / rolling. |
| Player stubs in DB | **live** — `wnba_player_game_stubs` (minutes, usage_proxy, pts/reb/ast/fg3m). |
| Checked-in 2025 / 2026-YTD advanced JSON pack | **missing** — DB is SoT when ingest has run. |
| Ch1 team prior pack filename | **missing** (next PR; **own name**, not `nba_team_prior_*.json`) |

**Verdict for B:** stats path **exists** → not B.

---

## 6. On disk / packs

| Asset | Status |
| ----- | ------ |
| `wnba_*` model-service pack | **exists** (poss-sim + props research) |
| Enterprise Ch1 prior JSON | **missing** |
| `kei_lines_wnba.json` / `power_ratings_wnba.json` | **missing** |
| Edge Board odds fallback | `apps/web/data/processed/edge_board_fallback_wnba.json` |
| NBA season-engine twin under `wnba_season_engine/` | **missing** (intentional — do not copy) |

---

## 7. Register (documentation only — not coded)

| Name                      | Value                         | Notes |
| ------------------------- | ----------------------------- | ----- |
| `MINUTE_GRID_SUM`         | `200`                         | 40-min × 5 — **not** NBA 240 |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50`          | Calendar tip years **2024 / 2025 / 2026** (midseason YTD heaviest) |
| `SITUATION_COEFFS`        | paper-sim on WNBA points      | **Forbidden:** copy NBA `home=+2.0`, `b2b=−1.5` from `nba_situation_coeffs_v0.json` |
| `PROP_PLAY_CAP_PER_SLATE` | `4`                           | Half of NBA’s 8 — register only |
| `ODDS_SPORT_KEY`          | `basketball_wnba`             | Already in `odds-api.ts` |

Poss-sim already uses home court **2.25** and rest multipliers — that is Chapter 0 research, **not** the registered Ch3 `SITUATION_COEFFS` paper-sim.

---

## 8. Forbidden check (this PR)

| Forbidden                                      | Honored |
| ---------------------------------------------- | ------- |
| Pack / emit / tags                             | Yes — docs only |
| Copy NBA pack / shrink / filenames             | Yes |
| Blend leftover Aug-1 KEI into prior            | Yes — documented, excluded |
| Team `if`                                      | Yes |
| CFB / NFL / NBA v0.1 edits                     | Yes |
| Promote research props to stake / Ch6          | Yes |
| Second engine beside `wnba-v1-poss-sim`        | Yes — Ch1 is a prior pack path, not a parallel sim |

---

## Done

- Audit complete; every item path or `missing`.
- Leftover board KEI identified (Aug 1 finals via fair-lines) — do not blend.
- **Next PR = A → Chapter 1 WNBA team prior (own shrink, own filename).**
- NBA stays parked. Fit / props / fantasy are not next.
