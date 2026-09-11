# P0 Odds Expansion — architecture + first slice

**Status:** first implementation PR (do **not** merge until Ryan/CoS review)  
**As of:** 2026-09-11  
**Base:** `deploy-vercel`  
**Goal:** 5M Odds capacity — market pipeline is **all available future game markets**, not current-week ingestion.

Hard locks for this PR:

- **#529 CFB public kill switch stays OFF** (`CFB_EDGE_BOARD_PUBLIC_ENABLED = false`)
- Do **not** retune KEI to match Vegas
- Do **not** flip the CFB public board
- HIST bulk backfill, DFS, #516, and merge are **out of scope**
- Numbers only — no new PLAY / LEAN stake chrome
- Never invent book prices, `as_of`, or Fair/KEI
- Extend `odds_snapshots` / `pull_odds_snapshot` / assemble — do **not** invent a parallel ledger

---

## Ryan deliverables → this PR

| Ryan ask                    | First-slice delivery                                                                                                                                                                                        | Follow-up (not this PR)                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **1. Odds without model**   | Verified-book rows paint MARKET + exact `market_as_of` when KEI/Fair is missing. Honest blank Fair.                                                                                                         | Per-sport Fair fill as models land                             |
| **2. Sorting**              | Shared horizon sort: live/current day → nearest upcoming → chronological future. Within the same kickoff window: freshest market, strongest book coverage, then best-line. **Not** giant model edges first. | Tune window size from live inventory                           |
| **3. Labels**               | `Current` / `Early Market` / `Futures · Advance Line` + exact `market_as_of`                                                                                                                                | Copy polish only                                               |
| **4. Odds lake fields**     | Canonical field contract + SQL view over existing `odds_snapshots` (append-only). OPEN / CURRENT / (CLOSE later) derived from history.                                                                      | CLOSE materialize at kickoff                                   |
| **5. Multi-book consensus** | Pure consensus helper: best, consensus, book count, dispersion, freshness; isolate rogue/stale. Not a KEI stand-in.                                                                                         | Wire onto customer Best formula (still **DO NOT INVENT** Best) |
| **6. Polling tiers**        | Config + `should_refresh` hook. Bulk `/odds` still one credit/sport (already paid). Tiers gate **per-event** catalog backfill so far-future is not polled at game-day rate.                                 | Cadence split by tier in beat                                  |
| **7. CFB kill switch**      | Untouched and tested still `false`                                                                                                                                                                          | Re-enable only after #529 gate                                 |

**Sports in scope:** CFB, NFL, NBA, NCAAM/CBB, MLB, NHL, WNBA — same `SPORT_MAP` / `SPORT_KEY_MAP`.

---

## Pipeline (market-driven)

```text
provider event catalog (/events)
        ↓
  bookmakers + markets (/odds)     ← ingest iff verified spread / total / ML
        ↓
  canonical game join (_ensure_hierarchy / games.external_id)
        ↓
  append-only odds_snapshots        ← never overwrite a captured vintage
        ↓
  lake view + OPEN/CURRENT/(CLOSE)
        ↓
  Edge Board assemble               ← odds-without-KEI allowed; Fair blank
```

**Do not artificially limit by current week.** If a verified mainline exists, persist and (where the customer surface is on) paint — even when kickoff is weeks/months away.

The Odds API bulk `GET /v4/sports/{sport}/odds` already returns every **upcoming event that currently has posted odds**. This PR:

1. Makes that “no week window” contract explicit (no `commenceTimeTo` cap).
2. Adds `/events` catalog discovery (3am / explicit `include_catalog`) for coverage: cataloged vs ingested.
3. Does **not** HIST-backfill and does **not** per-event-fetch every catalog ID on the hourly beat (credit bomb).

NFL **Week 1 customer tab** stays the live default (INC-2026-09-07: no live `daysAhead=200` fair-lines). Future NFL markets:

- **are ingested** into `odds_snapshots` with no week filter
- **appear on the live board** as odds-without-KEI extras when the Odds pull has verified books (Early Market / Futures labels)
- do **not** require a Fair/KEI print

---

## Odds without model (paint contract)

| Have                   | Fair / KEI                     | Market | `market_as_of`                               | Edge / Action            |
| ---------------------- | ------------------------------ | ------ | -------------------------------------------- | ------------------------ |
| Verified books, no KEI | blank (`—`) / “no house print” | paint  | required (book vintage; never request clock) | none                     |
| KEI, no books          | paint                          | blank  | none                                         | none                     |
| Both                   | paint                          | paint  | paint                                        | existing truth/tag rules |
| Neither                | do not invent a row            |        |                                              |                          |

PRE exhibitions stay off the NFL customer board. REG (and other-sport) odds-only rows stay.

---

## Horizon labels

| Label                      | When                                  |
| -------------------------- | ------------------------------------- |
| **Current**                | Live or same ET calendar day as `now` |
| **Early Market**           | Kickoff within 7 days, not today      |
| **Futures · Advance Line** | Kickoff more than 7 days out          |

Always show the exact `market_as_of` (row `linesAsOf` / book `last_update`). Never `Date.now()`.

---

## Lake field contract

Required on every lake row (view over existing snapshots — no parallel write table):

`sport`, `league`, `season`, `canonical_game_id`, `provider_event_id`, `book`, `market_type`, `side`, `line`, `price`, `retrieved_at`, `market_as_of`, `event_start`, `source`

Snapshot kind from **history**, never by overwriting:

- **OPEN** — first captured vintage for `(game, book, market, side)`
- **CURRENT** — latest captured vintage
- **CLOSE** — last legal pre-kickoff vintage (**later**; stub only this PR)

---

## Multi-book consensus (not KEI)

Given fresh quotes for one `(event, market)`:

- **best** — shop-side extreme (existing Best helper; formula still **UNKNOWN** for product math)
- **consensus** — median of non-isolated books
- **book_count** — n after dropping rogue/stale
- **dispersion** — IQR of lines
- **freshness** — max `market_as_of`
- **isolate** — stale vs peer vintage, or line outside 2.5× IQR

Consensus is **never** a Fair/KEI stand-in.

---

## Polling tiers

| Tier           | Horizon                            | Cadence intent                             |
| -------------- | ---------------------------------- | ------------------------------------------ |
| `far_future`   | > 7 days                           | Low — overnight catalog / 3am refresh only |
| `d7_plus`      | 7+ days (alias of far_future edge) | Moderate                                   |
| `d1_7`         | 1–7 days                           | Higher                                     |
| `game_day`     | same ET day                        | High                                       |
| `final_hours`  | last 6 hours                       | Highest                                    |
| movement boost | meaningful line change             | Elevate one tier                           |

Bulk `/odds` is one request per sport regardless of event count. Tiers **must not** be implemented as “re-pull `/odds` at game-day rate for dormant far-future” — that is already the cheap bulk path. Tiers gate **extra** per-event fetches.

---

## CFB

`apps/web/lib/cfb-edge-board-public.ts` — `CFB_EDGE_BOARD_PUBLIC_ENABLED = false`.  
This PR must not flip it, weaken assemble 503, or restore public CFB chrome.

---

## Code pointers

| Layer                                  | Path                                                  |
| -------------------------------------- | ----------------------------------------------------- |
| Design (this file)                     | `docs/ODDS_EXPANSION_P0.md`                           |
| Discovery / lake / consensus / polling | `services/model-service/src/services/odds_expansion/` |
| Ingest hook                            | `src.tasks.pull_odds_snapshot`                        |
| Lake SQL view                          | `infra/db/057_odds_expansion_lake.sql`                |
| Board horizon                          | `apps/web/lib/odds-horizon.ts`                        |
| Assemble                               | `apps/web/lib/build-edge-board-rows.ts`               |
| CFB kill switch                        | `apps/web/lib/cfb-edge-board-public.ts`               |
