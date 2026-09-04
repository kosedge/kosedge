# Odds + Data Infra — Overnight #5 honesty contract

**Status:** overnight **NARROW** honesty slice (Kos Edge #5) — not full Market/Odds Infrastructure  
**As of:** 2026-09-04  
**Base:** `deploy-vercel`  
**Alex live audit SoT:** www ~**01:32 ET** (fold into this PR)  
**Ryan scope:** FULL #5 locked separately; **this PR keeps shipping** honest empty fair-lines JSON + matrix + Lab DATA GAP inventory only.  
**Hard locks:** no invent odds / KEI / CLV / history · no PLAY/LEAN/PASS threshold flips · no casinoification · no Odds API key rotation/embed · no FRESH/AGING/STALE windows · no BEST/CONSENSUS/OPEN/CLOSE formula invent · CBB/NCAAM out unless a broken link needs an honest empty

---

## Contract (overnight)

1. **Never invent book prices.** Missing odds → empty lines + honest `slateStatus` / customer copy. Never mint `asOf` / `oddsAsOf` from request time.
2. **Prefer honest empty JSON 200** over bare HTML soft-404 when a Pro desk / API client expects `/api/{sport}/fair-lines`.
3. **NFL stays the live reference** — page-data proxies model-service; transport failures stay 503/504 (not fake empty).
4. **Non-NFL:** CFB / NCAAF alias not connected (model has no `/cfb/fair-lines`). MLB/NBA/NHL/WNBA proxy model-service when present; empty/offseason boards keep `asOf`/`oddsAsOf` null unless upstream supplies a real vintage. Envelope **matches NFL schema keys** (`season`, `currentWeek`, `window`, `diagnostics`, `slateStatus`, `lines`, …) with nulls/zeros — **no invent numbers**.
5. **Out of scope this slice:** full odds warehouse, historical backfill for Lab bias/CLV, key rotation (see DATA GAPs below).

---

## Live audit matrix (Alex · www.kosedge.com · ~01:32 ET / UTC 05:31–05:35)

| Sport         | Pre-fix `GET /api/{sport}/fair-lines`                                                               | Body / notes                                                                                                                                                                                     | After this PR                                                                                      |
| ------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| **nfl**       | **200 LIVE**                                                                                        | `count=241`, **9 books** (`draftkings`…`betonlineag`), `asOf`/`oddsAsOf` present · `diagnostics.oddsPersisted` **events/snapshots/history = 0** (CLV/history follow-up — **not** invent tonight) | unchanged                                                                                          |
| **cfb**       | **HTML soft-404**                                                                                   | no JSON route · model `/cfb/fair-lines` 404                                                                                                                                                      | **200** honest empty NFL-shaped JSON (`slateStatus=not_connected`)                                 |
| **ncaaf**     | **HTML soft-404** (API) · `/pro/ncaaf/kei-lines` **404** (cfb kei-lines already **308**→fair-lines) | Odds-API alias of CFB                                                                                                                                                                            | **200** `/api/ncaaf/fair-lines` ≡ CFB empty · `/pro/ncaaf/kei-lines` **308**→`/pro/cfb/fair-lines` |
| **mlb**       | **HTML soft-404**                                                                                   | model 200 `count=0`, no as-of                                                                                                                                                                    | **200** proxy / empty `no_slate`                                                                   |
| **nba**       | **HTML soft-404**                                                                                   | model 200 with sim rows                                                                                                                                                                          | **200** proxy                                                                                      |
| **nhl**       | **HTML soft-404**                                                                                   | model `offseason_empty`                                                                                                                                                                          | **200** proxy / empty                                                                              |
| **wnba**      | **HTML soft-404**                                                                                   | model thin live                                                                                                                                                                                  | **200** proxy                                                                                      |
| **ncaam/cbb** | out                                                                                                 | —                                                                                                                                                                                                | desk copy only — no warehouse                                                                      |

Hypothesis confirmed pre-fix: **NFL fair-lines 200 LIVE (241 / 9 books); others HTML-404.**

---

## Post-slice API contract

| Sport     | Route                   | Behavior                                                                                             |
| --------- | ----------------------- | ---------------------------------------------------------------------------------------------------- |
| nfl       | `/api/nfl/fair-lines`   | Unchanged — live proxy; 503/504 on transport                                                         |
| cfb       | `/api/cfb/fair-lines`   | **200** honest empty · NFL-shaped · `slateStatus=not_connected` · `asOf`/`oddsAsOf`=null · `count=0` |
| ncaaf     | `/api/ncaaf/fair-lines` | Same handler as CFB (alias)                                                                          |
| mlb       | `/api/mlb/fair-lines`   | **200** proxy · empty → `no_slate` · never invent as-of                                              |
| nba       | `/api/nba/fair-lines`   | **200** proxy · preserve upstream `slateStatus` / lines                                              |
| nhl       | `/api/nhl/fair-lines`   | **200** proxy · offseason empty stays empty                                                          |
| wnba      | `/api/wnba/fair-lines`  | **200** proxy · preserve upstream status                                                             |
| ncaam/cbb | —                       | **Out** — no new API                                                                                 |

Shared envelope (`apps/web/lib/fair-lines-api-board.ts`) — NFL-shaped:

```ts
{
  sport: string;
  season: number | null;
  modelVersion: string;
  asOf: string | null;      // never Date.now()
  oddsAsOf: string | null;  // never Date.now()
  currentWeek: number | null;
  count: number;
  lines: unknown[];
  slateStatus: string;
  message: string;          // includes “we do not invent…” when empty
  window: { daysAhead: number; includePastDays: number };
  diagnostics: {
    oddsFeedStatus: string;
    oddsFeedError: string | null;
    oddsEventsSeen: number;
    marketJoinedCount: number;
    bookmakers: string[];
    kosedgeOnly: boolean;
    oddsPersisted: {
      eventsPersisted: number;
      snapshotsInserted: number;
      historyUpserted: number;
    };
  };
}
```

Desk redirects: `/pro/{sport}/kei-lines` → fair-lines (existing) + **`/pro/ncaaf/kei-lines` → `/pro/cfb/fair-lines`** (308 permanent).

---

## Lab DATA GAP inventory (list only — no fake fill)

| Gap                                              | Why it blocks Lab / product                                                        | Honest stance                                                       |
| ------------------------------------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Historical odds warehouse                        | Lab bias / CLV need open→close series                                              | **N/A—DATA GAP** until owned (`docs/lab/*`)                         |
| NFL `oddsPersisted` = 0 at probe                 | Subscriber GET uses `persist=0`; events/snapshots/history not landing on this path | CLV/history follow-up — **do not invent** open/close or CLV tonight |
| CFB model fair-lines                             | No `/cfb/fair-lines` on model-service                                              | Season engine ≠ handicap KEI board                                  |
| MLB/NBA/NHL/WNBA `as_of` / `odds_as_of` on model | Non-NFL boards omit book vintage stamps                                            | Leave null until Odds join lands stamps                             |
| Odds API key rotation                            | Ops hygiene                                                                        | Explicitly **out of scope** this overnight                          |
| Full multi-sport odds persist path               | Training / CLV                                                                     | Beat/worker owns NFL persist; do not write from subscriber GET      |
| Signed bias / CLV series for Lab scorecards      | Market Edge Evidence GREEN needs owned series                                      | Mark **N/A—DATA GAP** — no synthetic fill                           |

---

## Required market defs — TO BE LOCKED (from audit evidence)

Ryan locked **FULL #5** (Market / Odds Infrastructure). **This PR stays NARROW:** honest empty fair-lines JSON + matrix + DATA GAP inventory only.

The following definitions are **required** for full #5 but are **not filled tonight**. Do **not** invent FRESH/AGING/STALE windows, BEST/CONSENSUS formulas, OPEN/CLOSE calc changes, historical backfill, or PLAY flips in this slice. Lock each from owned audit evidence in a separate architecture / risk-register follow-up.

| Def                         | Status tonight | Lock later from                                                                               |
| --------------------------- | -------------- | --------------------------------------------------------------------------------------------- |
| **OPEN**                    | TO BE LOCKED   | First-captured book open (line + price); immutable once set — no invent open=current          |
| **CURRENT**                 | TO BE LOCKED   | Latest joined book quote (line + price) with real vintage                                     |
| **BEST**                    | TO BE LOCKED   | Shop-side best across carried books — formula TBD from inventory evidence                     |
| **CONSENSUS**               | TO BE LOCKED   | Market average / consensus rule — formula TBD; never a stand-in for KEI                       |
| **CLOSE**                   | TO BE LOCKED   | Closing line at kickoff / final — requires owned history series                               |
| **AS-OF**                   | TO BE LOCKED   | Book `last_update` / `odds_captured_at` only — never request clock                            |
| **Line + price**            | TO BE LOCKED   | Pairing rules (spread/total/ML with American price) per market                                |
| **Append-only history**     | TO BE LOCKED   | Snapshot / history write path (events → snapshots → history); tonight probe `oddsPersisted=0` |
| **Fail toward uncertainty** | TO BE LOCKED   | When books missing → empty / unavailable / honest `slateStatus` — never invent numbers        |

Architecture audit + risk register = **separate follow-up**. Not this PR.

---

## Code pointers

- NFL page-data: `apps/web/app/api/nfl/fair-lines/route.ts`
- Shared honesty envelope: `apps/web/lib/fair-lines-api-board.ts`
- Non-NFL page-data: `apps/web/app/api/{cfb,ncaaf,mlb,nba,nhl,wnba}/fair-lines/route.ts`
- NCAAF desk alias redirects: `apps/web/next.config.ts`
- Desk fail-closed copy: `apps/web/app/(pro)/pro/[sport]/fair-lines/page.tsx`
