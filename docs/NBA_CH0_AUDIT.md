# NBA Chapter 0 — discovery audit

**Phase:** Audit only. No pack / KEI / tags / props emit.  
**As of:** `2026-09-01`  
**Brief:** [`docs/NBA_CH0_DISCOVERY_BRIEF.md`](./NBA_CH0_DISCOVERY_BRIEF.md)  
**Plan:** [`artifacts/NBA_ENTERPRISE_PLAN.md`](../artifacts/NBA_ENTERPRISE_PLAN.md)

Every row is a **path** or **`missing`**. Do not invent Odds keys or ratings.

---

## Decision — next PR

| Pick  | Condition         | Result                                          |
| ----- | ----------------- | ----------------------------------------------- |
| **A** | Market exists     | → Chapter 1 team prior                          |
| B     | No NBA Stats path | → fetcher, then Ch1                             |
| C     | Market missing    | → wire `basketball_nba` first, still no ratings |

### **Pick: A**

- `basketball_nba` is already mapped in the web Odds client and training/historical pull scripts.
- NBA Stats / data.nba.com ingest already lives in `nba_data.py` (no new vendor required for Ch1).
- Therefore: **Chapter 1 one-year team prior + shrink** is the next PR — temporary shell, like CFB carry. Still **no** props, **no** KEI emit, **no** tags.

Not B: stats path exists. Not C: market key is live for mainlines (and props markets are named in the training pull).

---

## 1. Product — `/pro/nba`

Static NBA tree is thin (`apps/web/app/(pro)/pro/nba/` = `layout.tsx` + `fair-lines/`). Most desk pages are shared `[sport]` routes.

| Surface                | Path                                                                     | Status              | Notes                                                                           |
| ---------------------- | ------------------------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------- |
| Overview               | `/pro/nba/overview` → `apps/web/app/(pro)/pro/[sport]/overview/page.tsx` | **live**            | Hub; `getTonightGames("nba")`; honest empty offseason                           |
| Edge Board             | `/edge-board/nba` → `apps/web/app/edge-board/[sport]/page.tsx`           | **live**            | Odds + fair-lines KEI join; fallback JSON empty by design                       |
| Edge Board (pro alias) | `/pro/edge-board/nba`                                                    | **missing**         | NFL has `/pro/nfl/edge-board` redirect; NBA does not                            |
| Slate                  | `/pro/nba/slate/today` → `…/[sport]/slate/[date]/page.tsx`               | **live**            | Matchup cards from Odds; empty-honest when no events                            |
| Ratings                | `/pro/power-ratings/nba` → `…/power-ratings/[sport]/page.tsx`            | **shell**           | No `power_ratings_nba.json`; “Ratings feed pending…”                            |
| Ratings (nba subtree)  | `/pro/nba/ratings`                                                       | **missing**         |                                                                                 |
| Teams                  | `/pro/nba/teams` → `…/[sport]/teams/**`                                  | **shell**           | 30-team directory; most detail sections `pending`                               |
| Props                  | `/pro/nba/props` → `…/[sport]/props/page.tsx` + `lib/nba-props-board.ts` | **live (research)** | Calls model-service `/nba/props/board`; **not** Ch6 — stub means, no stake tags |
| Fair Lines             | `/pro/nba/fair-lines`                                                    | **live**            | Static page; `fetchNbaFairLines`                                                |
| Fantasy                | `/pro/nba/fantasy`                                                       | **missing**         | NFL-only under `pro/nfl/fantasy/**`                                             |
| Futures / projections  | `/pro/nba/futures` · `/pro/nba/projections`                              | **missing**         | NFL: `/pro/nfl/projections`                                                     |
| Camp                   | `/pro/nba/camp`                                                          | **missing**         | NFL: `/pro/nfl/camp`                                                            |
| Injuries               | `/pro/nba/injuries`                                                      | **shell / partial** | RSS headlines (`sport-injury-news.ts`); designation table pending               |
| Standings              | `/pro/nba/standings`                                                     | **missing\***       | Route file NFL-gates → `notFound()` for NBA (nav still links)                   |
| Stats / pace           | `/pro/nba/stats`                                                         | **missing\***       | Same NFL-only `notFound()`                                                      |
| KEI Lines hub          | `/pro/kei-lines/nba`                                                     | **shell**           | No `kei_lines_nba.json`; fair-lines is the live KEI surface                     |
| Odds compare           | `/odds/nba`                                                              | **live**            | `odds-api.ts` → `basketball_nba`                                                |

\*Route file exists under `[sport]` but hard-404s for NBA.

### NFL surfaces with **no** NBA twin

`/pro/nfl/fantasy` (+ builder/mock/…) · `weekly-fantasy` · `camp` · `projections` · `survivor` · `awards` · `boards` · `dfs` · `game-boxes` · `model` · `news` · `previews` · `player-previews` · `launch-notes`

---

## 2. Market — Odds / `basketball_nba`

| Question                                      | Finding                                                                                                                                                                                                                                 |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Does Odds client call `basketball_nba`?       | **Yes** — `apps/web/lib/odds-api.ts` `SPORT_KEY_MAP.nba = "basketball_nba"` (mainlines: spreads / totals / h2h). Also `scripts/odds/enterprise_training_pull.py`, `persist_mainline_odds.py`, `tasks.pull_nba_historical_odds_densify`. |
| Trusted books                                 | **Shared** `ALLOWED_BOOKS` in `odds-api.ts` (DK, FD, BetMGM, BetRivers, Hard Rock, Fanatics, bet365, Circa, Betr). No NBA-only allowlist. Training densify defaults DK+FD.                                                              |
| Live web fetch of player props?               | **No** — web Odds client does not request player prop markets for NBA tonight boards.                                                                                                                                                   |
| Training / warehouse prop keys (in code only) | Odds API → stored key in `enterprise_training_pull.py`: `player_points`→`pts`, `player_rebounds`→`reb`, `player_assists`→`ast`, `player_threes`→`threes`, `player_points_rebounds_assists`→`pra`.                                       |
| Engine prop markets joined today              | `nba_player_prop_projection.NBA_PROP_MARKETS = ("pts","reb","ast","threes")` — **no `pra`** in the live join.                                                                                                                           |

Do **not** invent additional Odds keys in Ch1 code.

---

## 3. Engine — model-service

| Item                        | Path / status                                                                                                                                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes                      | `services/model-service/src/routes/nba.py` — `/nba/health`, `/fair-lines`, `/props/board`, `/ops/*`, simulations                                                                  |
| Possession sim (team lines) | `nba_possession_simulator.py` · publish `nba_publish_policy.py` · cal `nba_calibration.py`                                                                                        |
| Stub props (research)       | `nba_player_prop_projection.py` · `nba_prop_edge_policy.py` · version `nba-player-props-v1`                                                                                       |
| Schema / SQL                | `nba_schema.py` · `infra/db/045_nba_model_foundation.sql` · `046_nba_player_props.sql`                                                                                            |
| Ingest                      | `nba_data.py` — **stats.nba.com** + **data.nba.com** (optional SportsDataIO via env). Tasks: `pull_nba_schedule_ingest`, `pull_nba_season_ingest`, …                              |
| `nba_api` Python package    | **missing** (not required — HTTP to NBA Stats already wired)                                                                                                                      |
| Shared CBB engine           | **Do not break** shared Odds clients (`basketball_ncaab`) and edge-board sport keys. No shared CBB possession/prop engine under `nba_*`. WNBA is a parallel pack — keep separate. |
| Ops plan (legacy phases)    | `data/ops/nba-model-build-plan.md` — Phase 0–3 research scaffold; **superseded as product spine by** `artifacts/NBA_ENTERPRISE_PLAN.md`                                           |

---

## 4. On disk

| Asset                                 | Status                                                                                   |
| ------------------------------------- | ---------------------------------------------------------------------------------------- |
| 2026–27 schedule file (checked-in)    | **missing** — schedule intended via DB ingest (`nba_games_ingest`), not a repo JSON pack |
| 2025–26 team advanced (checked-in)    | **missing** — rolling features live in DB tables when ingest has run                     |
| Multi-year player tables (checked-in) | **missing** — stubs/box in DB; no `0.20/0.30/0.50` player talent pack yet (Ch2)          |
| Injury ingest (model-service)         | **missing** — web RSS only (`apps/web/lib/sport-injury-news.ts`)                         |
| Edge Board fallback                   | `apps/web/data/processed/edge_board_fallback_nba.json` (empty offseason)                 |
| Power / KEI JSON packs                | **missing** (`power_ratings_nba.json`, `kei_lines_nba.json`)                             |

Ch1 may introduce a **team prior pack** (allowlisted then). Ch0 does not.

---

## 5. NFL props miss — do not copy

NFL prop means are produced in `nfl_player_projection_engine.py` and unified onto `PlayerGameProduction` in `nfl_player_production.py`; fantasy scores that **same** production vector (`fantasy_points_from_projection`), and the production-spine rule forbids a separate fantasy engine. The miss NBA must not repeat is the earlier **sidecar**: a props board that blended baselines / box-MC / prop-cal into means fantasy did not read (`data/ops/nfl-props-confidence-20260819.md`, `nfl-spine-unify-phase1-20260819.md`, `.cursor/rules/nfl-production-spine.mdc`). **NBA today already has a lighter version of that risk:** `NbaPlayerPropProjection` (stub minutes × per-min rates) is independent of the possession-sim team totals — research-only scaffolding. Ch6 props and Ch7 fantasy wait for Ch5 `PlayerProjection`. Dark week with no tags beats a fake desk.

---

## 6. Register (documentation only — not coded)

| Name                      | Value                | Notes                                                      |
| ------------------------- | -------------------- | ---------------------------------------------------------- |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50` | Ch2 — on **players**, not three seasons of team net rating |
| `MINUTE_GRID_SUM`         | `240`                | Ch2 / Ch5                                                  |
| `PROP_PLAY`               | `≥ 4.0 AND ≥ 0.6σ`   | Ch6 — after `PlayerProjection`                             |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                  | Ch6                                                        |
| `ODDS_SPORT_KEY`          | `basketball_nba`     | Already in `odds-api.ts`                                   |

---

## 7. Forbidden check (this PR)

| Forbidden                                   | Honored                                             |
| ------------------------------------------- | --------------------------------------------------- |
| Pack / emit / tags                          | Yes — docs + plan only                              |
| Team `if`                                   | Yes                                                 |
| DARKO/EPM/CTG as SoT                        | Yes                                                 |
| CFB / NFL edits                             | Yes — no model or web changes outside NBA docs/plan |
| Props tab without `PlayerProjection` as Ch6 | Yes — existing research props audited, not promoted |
| Sneaky NFL prop rewrite                     | Yes                                                 |

---

## Done

- Enterprise plan locked.
- Audit complete; every item path or `missing`.
- **Next PR = A → Chapter 1 team prior + shrink.**
- Do not start Ch1 until this merges. Fit/props/fantasy are not next.
