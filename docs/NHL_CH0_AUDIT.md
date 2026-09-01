# NHL Chapter 0 — discovery audit

**Phase:** Audit only. No pack / tags / filling blank KEINHL.  
**As of:** `2026-09-01`  
**Clock:** camps ~**Sep 16** · preseason **Sep 19–26** · open **Sep 29** (~**84** games)  
**Brief:** [`docs/NHL_CH0_DISCOVERY_BRIEF.md`](./NHL_CH0_DISCOVERY_BRIEF.md)

Every row is a **path** or **`missing`**. Do not invent Odds keys or ratings.  
**Do not copy the NBA / WNBA pack.** Own constants and filenames when Ch1 starts.

---

## Decision — next PR

| Pick  | Condition              | Result                                                                               |
| ----- | ---------------------- | ------------------------------------------------------------------------------------ |
| A     | Market + stats exist   | → Chapter 1 prior (`NHL_TEAM_CARRY_SHRINK`, `nhl_team_prior_2026.json`)               |
| **B** | No NHL stats path      | → **fetcher**, then Ch1                                                              |
| C     | Hidden KEINHL leftover | → document, don’t blend                                                              |

### **Pick: B**

- **Market exists:** `icehockey_nhl` is mapped in the web Odds client; `/edge-board/nhl` and `/odds/nhl` are live markets surfaces; training pull checkpoint marks `nhl:mainlines` / `nhl:props` completed.
- **Stats path for a team prior does not exist:** no `nhl_data.py`, no `infra/db` NHL SQL, no model-service `nhl_*` routes/engines, no checked-in 2026–27 schedule, no 2025–26 team GF/GA tables, no multi-year skater/goalie warehouse. ESPN scoreboard is wired only for Goalie Desk probables — that is **not** a Ch1 GF/GA prior path. SportsDataIO NHL endpoints are a **replay catalog** only (`sportsdata_replay_endpoints.json`), not a live ingest module. NHL.com / `statsapi.web.nhl` / `api-web.nhle` → **`missing`**.
- Therefore: **next PR = fetcher (schedule + 2025–26 team GF/GA at minimum), then Chapter 1 own prior** — still **no** pack in this PR, **no** filling KEINHL, **no** NBA/WNBA copy.

**Not A:** markets alone are insufficient without a stats path for team carry.  
**Not C:** board KEI is **intentionally empty** (honest markets-only), not a hidden leftover printing fake numbers — see §0.

---

## 0. Board KEINHL honesty (read first)

Live `/edge-board/nhl` is **markets only**. KEINHL is **not** shipping numbers.

| Surface     | What prints                                                                 | Source                                                                 |
| ----------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| KEI column  | **blank** (`—`)                                                             | `resolveKeiGames("nhl")` → `[]`                                        |
| Live books  | Spreads / totals from Odds (or Jul 31 fallback when Odds empty)             | `odds-api.ts` → `icehockey_nhl` · `edge_board_fallback_nhl.json`       |
| Banner copy | `KEINHL handicap is not shipped — KEI stays blank (books ≠ KEI). …`         | `apps/web/app/edge-board/[sport]/page.tsx`                            |
| Board chrome| `Markets only · KEINHL handicap not shipped yet · ET` (+ longer empty copy) | `apps/web/components/EdgeBoard.tsx`                                    |

Resolve path:

```text
edge-board / slate / overview (tonight games)
  → loadAssembledEdgeBoardRows("nhl") / getTonightGames("nhl")
  → resolveKeiGames("nhl") → []          apps/web/lib/resolve-kei-lines.ts
  → sportIsMarketsOnlyEdgeBoard("nhl")   apps/web/lib/edge-board-kei-availability.ts
  → books from Odds or fallback JSON; KEI / Edge / Tag stay empty
```

Brand code only: `apps/web/lib/kei-brand.ts` → `nhl: "KEINHL"` (label, not a model).  
File KEI pack: **`missing`** (`kei_lines_nhl.json`).  
Ops lock: `data/ops/edge-board-population-status-2026-08-02.md` — NHL Markets **Yes** / KEI **No**.

**Ch0 / Ch1 must not fill these blanks.** There is no leftover fair-lines row to blend (contrast WNBA Aug-1 finals). Pick C does not apply.

Props page today: shell copy only — “Props board pending”; no model-service `/nhl/props/board`.

---

## 1. Product — `/pro/nhl` · `/edge-board/nhl`

Static NHL tree under `apps/web/app/(pro)/pro/nhl/` → **`missing`**. Most desk pages are shared `[sport]` routes (same thin-hub pattern as NBA/WNBA).

| Surface                | Path                                                                        | Status                   | Notes                                                                                          |
| ---------------------- | --------------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------- |
| Overview               | `/pro/nhl/overview` → `apps/web/app/(pro)/pro/[sport]/overview/page.tsx`    | **live**                 | Hub; `getTonightGames("nhl")` + 8s `Promise.race` empty fallback                               |
| Edge Board             | `/edge-board/nhl` → `apps/web/app/edge-board/[sport]/page.tsx`              | **markets-only (live)**  | Odds + blank KEI; KEINHL-not-shipped banner                                                    |
| Edge Board (pro alias) | `/pro/nhl/edge-board` or `/pro/edge-board/nhl`                              | **missing**              | Desk footer links `/edge-board/nhl`                                                            |
| Slate                  | `/pro/nhl/slate/today` → `…/[sport]/slate/[date]/page.tsx`                  | **live**                 | Matchup cards from board; goalie framing in desk copy                                          |
| Goalie Desk            | `/pro/nhl/goalies` → `…/[sport]/goalies/page.tsx`                           | **live / partial**       | ESPN probables via `nhl-goalie-confirmation.ts`; honest Pending when no name                   |
| Props                  | `/pro/nhl/props` → `…/[sport]/props/page.tsx`                               | **shell**                | “Props board pending”; slate context via `getTonightGames` only — **not** Ch6                  |
| Fantasy                | `/pro/nhl/fantasy`                                                          | **missing**              | NFL + NBA/WNBA Ch7 only                                                                        |
| Fair Lines             | `/pro/nhl/fair-lines`                                                       | **shell**                | No KEI → falls back to `getTonightGames` market rows                                           |
| Edges                  | `/pro/nhl/edges`                                                            | **shell**                | Board-derived; KEI edges blank on markets-only                                                 |
| Ratings / power        | `/pro/power-ratings/nhl`                                                    | **shell / missing pack** | No `power_ratings_nhl.json`                                                                    |
| Ratings alias          | `/pro/nhl/ratings`                                                          | **missing**              |                                                                                                |
| KEI Lines hub          | `/pro/kei-lines/nhl`                                                        | **shell**                | Markets-only empty copy; no `kei_lines_nhl.json`                                               |
| Teams                  | `/pro/nhl/teams` → `…/[sport]/teams/**`                                     | **shell**                | 32-team directory (`NHL_TEAM_DIRECTORY`)                                                       |
| Injuries               | `/pro/nhl/injuries`                                                         | **shell / partial**      | RotoWire RSS (`sport-injury-news.ts`)                                                          |
| Standings              | `/pro/nhl/standings`                                                        | **missing\***            | `[sport]/standings` NFL-gates → `notFound()`                                                  |
| Stats / pace           | `/pro/nhl/stats`                                                            | **missing\***            | Same NFL-only `notFound()`                                                                     |
| Odds compare           | `/odds/nhl`                                                                 | **live**                 | `odds-api.ts` → `icehockey_nhl`                                                                |

\*Route file exists under `[sport]` but hard-404s for NHL (nav still links standings).

Nav/config: `apps/web/lib/sport-pro-nav.ts` — Goalie Desk primary extra; tools include Injuries, Standings, “Limited Props”, “KEI (not shipped)”.  
Desk path label: Fair Lines → Edges → Goalie Desk (`pro-sport-desk.ts`).

### Overview — same RSC trap as NBA?

| Question                                      | Finding                                                                                                                                                                      |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shared overview page?                         | **Yes** — `apps/web/app/(pro)/pro/[sport]/overview/page.tsx` for both NBA and NHL.                                                                                           |
| What does NHL overview call?                  | **`getTonightGames(sportKey)` only** (via direct assemble). **Does not** call fair-lines / `resolveKeiGames` / model-service.                                                |
| Hang class (self-HTTP edge-board assemble)    | **Already fixed** for all sports — `loadAssembledEdgeBoardRows` / `getTonightGames` direct assemble (`data/ops/multi-sport-ui-overhaul-report.md`; edge-board page comment). |
| Hardening on overview                         | **`Promise.race(..., 8_000)`** → empty array (`tonightGamesEmpty`). Same race for NBA and NHL.                                                                               |
| NBA-specific fair-lines RSC path on overview? | **No** on this page. NHL has **no** fair-lines model call to hang on.                                                                                                        |
| Verdict                                       | **Same shared board-pull + race fix as NBA overview.** Not a separate leftover KEI/fair-lines RSC trap. Leave alone.                                                         |

### Goalie Desk / starter confirmation

| Item       | Path / finding                                                                                                                                      |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lib        | `apps/web/lib/nhl-goalie-confirmation.ts`                                                                                                           |
| Tests      | `apps/web/__tests__/lib/nhl-goalie-confirmation.test.ts`                                                                                            |
| Behavior   | ESPN `site.api.espn.com/.../hockey/nhl/scoreboard` → `competitors[].probables[0]` → confirmed / expected / pending                                  |
| Invents?   | **No** — no name → Pending                                                                                                                          |
| Warehouse  | **missing** — UI confirmation only; not a starter ingest table                                                                                      |
| Gate (reg) | Documented only: `STARTER_GATE` = `unknown` → **no goalie PLAY** (Ch6 later). Unknown starter must not unlock goalie stake tags when props arrive. |

---

## 2. Market — Odds / `icehockey_nhl`

| Question                                      | Finding                                                                                                                                                                                     |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Does Odds client call `icehockey_nhl`?        | **Yes** — `apps/web/lib/odds-api.ts` `SPORT_KEY_MAP.nhl = "icehockey_nhl"` (mainlines: spreads / totals / h2h). Also `scripts/odds/enterprise_training_pull.py`, `persist_mainline_odds.py`. |
| Trusted books                                 | **Shared** `ALLOWED_BOOKS` (no NHL-only allowlist).                                                                                                                                         |
| Live web fetch of player props?               | **No** — web Odds client requests mainlines only for boards.                                                                                                                                |
| Training prop keys (coded)                    | Odds API → stored: `player_points`→`pts`, `player_goals`→`goals`, `player_assists`→`assists`, `player_shots_on_goal`→`sog`.                                                                 |
| **G / A / P / SOG / saves?**                  | **G / A / P / SOG coded** (`goals` / `assists` / `pts` / `sog`). **`player_saves` / saves → `missing`** in coded market lists.                                                              |
| Prop keys “actually returned” (warehouse)     | Checkpoint `data/ops/odds-enterprise-training-pull/checkpoint.json`: `nhl:props` **822 dates** (pulled 2026-07-27); `nhl:mainlines` **1464 dates**. Summary inventory zeros are stale vs checkpoint. Agent host has **no** live Odds re-hit in this audit — code + checkpoint are the evidence. |
| Engine prop markets joined today              | **`missing`** — no model-service NHL props board.                                                                                                                                           |

Do **not** invent additional Odds keys (including saves) in a future Ch1 prior PR.

---

## 3. Engine — model-service (`nhl_*` leftovers?)

| Item                         | Path / status                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------- |
| Routes (`nhl.py`)            | **`missing`** — existing: `nba.py`, `wnba.py`, `nfl.py`, `mlb.py`, `cfb.py`, … |
| Grep `nhl` / `icehockey` / `hockey` under `services/model-service` | **`missing`** (no engines, tasks, schema modules)             |
| Schema / SQL (`infra/db`)    | **`missing`** NHL migration                                                   |
| Possession / team sim        | **`missing`**                                                                 |
| Props projection             | **`missing`**                                                                 |
| Fair-lines API               | **`missing`**                                                                 |
| Shared NBA/WNBA engines      | **Do not import.** Odds client sport map only.                                |

**Verdict for leftover engines:** no hidden `nhl_*` model pack to blend. Brand code `KEINHL` exists in web chrome only.

---

## 4. Data assets — schedule / GF·GA / skaters / goalies / starters

| Asset                                         | Status                                                                                                                                   |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 2026–27 schedule (checked-in)                 | **`missing`**                                                                                                                            |
| Schedule ingest (first-party NHL pipeline)    | **`missing`** — ESPN scoreboard only inside goalie confirmation lib                                                                      |
| 2025–26 team GF/GA tables                     | **`missing`** (narrative cite in writer content only — not a data SoT)                                                                   |
| Multi-year skater tables                      | **`missing`**                                                                                                                            |
| Multi-year goalie tables                      | **`missing`**                                                                                                                            |
| Starter ingest (warehouse)                    | **`missing`** — ESPN probables UI path only (`nhl-goalie-confirmation.ts`)                                                               |
| Stats path without a new vendor?              | **ESPN scoreboard coded** (goalies). **NHL public stats APIs:** **`missing`**. SportsDataIO: **replay catalog only**, not live ingest. |
| Team directory                                | `apps/web/lib/team-research/directories-pro.ts` — `NHL_TEAM_DIRECTORY` (32)                                                              |
| Team research sections                        | `sport-config.ts` `hockeySections()` — all `pending`                                                                                     |
| Edge Board odds fallback                      | `apps/web/data/processed/edge_board_fallback_nhl.json` (captured `2026-07-31`; 31 events / 62 spread+total rows)                        |
| `power_ratings_nhl.json` / `kei_lines_nhl.json` | **`missing`**                                                                                                                          |
| Enterprise Ch1 prior JSON                     | **`missing`** (next chapter after fetcher; own name `nhl_team_prior_2026.json`)                                                          |
| `artifacts/*NHL*` enterprise plan             | **`missing`**                                                                                                                            |

**Verdict for B:** stats path for Ch1 team prior **does not exist** → **B**.

Fetcher scope hint (next PR, not this one): schedule + 2025–26 team GF/GA without standing up a second vendor religion if a public NHL/ESPN path can carry; SportsDataIO remains optional catalog, not a requirement to invent here.

---

## 5. Register (documentation only — not coded)

| Name                      | Value                | Notes                                                                 |
| ------------------------- | -------------------- | --------------------------------------------------------------------- |
| `ODDS_SPORT_KEY`          | `icehockey_nhl`      | Already in `odds-api.ts`                                              |
| `PLAYER_YEAR_WEIGHTS`     | `0.20 / 0.30 / 0.50` | Later player talent — on **players**, not three seasons of team GF/GA |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                  | Between NBA’s 8 and WNBA’s 4 — register only                          |
| `STARTER_GATE`            | `unknown` → no PLAY  | Goalie props: unknown starter ⇒ **no goalie PLAY**                    |

Ch1 names reserved (not coded here): `NHL_TEAM_CARRY_SHRINK`, `nhl_team_prior_2026.json`.

---

## 6. Forbidden check (this PR)

| Forbidden                          | Honored                                      |
| ---------------------------------- | -------------------------------------------- |
| Pack / emit / tags                 | Yes — docs only                              |
| Fill blank KEINHL                  | Yes — documented empty, untouched            |
| Copy NBA / WNBA shrink / filenames | Yes                                          |
| Team `if`                          | Yes                                          |
| NBA / WNBA / CFB / NFL edits       | Yes                                          |
| Promote Limited Props shell to Ch6 | Yes                                          |
| Blend leftover board KEI           | Yes — none present; markets-only left honest |

---

## Done

- Audit complete; every item path or `missing`.
- Prod board is markets-only; KEINHL blank stays blank.
- No hidden `nhl_*` model leftover; brand label only.
- Odds keys coded: G / A / P / SOG; **saves missing**.
- Overview shares NBA’s board-pull + 8s race fix — not a fair-lines RSC trap.
- **Next PR = B → fetcher (stats path), then Chapter 1 NHL team prior (own shrink, own filename).**
- Do not start Ch1 in this PR. NBA / WNBA / CFB / NFL stay parked.
