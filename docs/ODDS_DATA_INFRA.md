# Odds + Data Infra — Overnight #5 honesty contract

**Status:** overnight first honesty slice (Kos Edge #5)  
**As of:** 2026-09-04  
**Base:** `deploy-vercel`  
**Hard locks:** no invent odds / KEI / CLV / history · no PLAY/LEAN/PASS threshold flips · no casinoification · no Odds API key rotation/embed · CBB/NCAAM out unless a broken link needs an honest empty

---

## Contract (overnight)

1. **Never invent book prices.** Missing odds → empty lines + honest `slateStatus` / customer copy. Never mint `asOf` / `oddsAsOf` from request time.
2. **Prefer honest empty JSON 200** over bare HTML 404 when a Pro desk expects `/api/{sport}/fair-lines`.
3. **NFL stays the live reference** — page-data proxies model-service; transport failures stay 503/504 (not fake empty).
4. **Non-NFL:** CFB is not connected (model has no `/cfb/fair-lines`). MLB/NBA/NHL/WNBA proxy model-service when present; empty/offseason boards keep `asOf`/`oddsAsOf` null unless upstream supplies a real vintage.
5. **Out of scope this slice:** full odds warehouse, historical backfill for Lab bias/CLV, key rotation (see DATA GAPs below).

---

## Live audit matrix (pre-fix · www.kosedge.com)

Probe UTC **2026-09-04T05:31Z** (unauthenticated; open-access preview authorizes NFL).

| Sport | `GET /api/{sport}/fair-lines` | Body notes | Model-service `/{sport}/fair-lines` |
| ----- | ----------------------------- | ---------- | ----------------------------------- |
| **nfl** | **200** | `asOf`, `oddsAsOf`, `count` present (`count` > 0) | **200** · `as_of` / `odds_as_of` / `count` |
| **cfb** | **404** (HTML) | no JSON route | **404** `{"detail":"Not Found"}` |
| **mlb** | **404** (HTML) | no JSON route | **200** · `count=0`, no `as_of` / `odds_as_of` |
| **nba** | **404** (HTML) | no JSON route | **200** · `slate_status`, `count` (live sim rows) |
| **nhl** | **404** (HTML) | no JSON route | **200** · `slate_status=offseason_empty`, `count=0` |
| **wnba** | **404** (HTML) | no JSON route | **200** · `slate_status`, thin live count |

Hypothesis confirmed: **NFL fair-lines 200; CFB (and other non-NFL) fair-lines API 404** before this slice.

Desk HTML (separate from API): `/pro/{sport}/fair-lines` shells exist for MLB/NBA/WNBA (SSR via model fetch) and CFB/NHL via `/pro/[sport]/fair-lines` (fail-closed pending copy).

---

## Post-slice API contract

| Sport | Route | Behavior |
| ----- | ----- | -------- |
| nfl | `/api/nfl/fair-lines` | Unchanged — live proxy; 503/504 on transport |
| cfb | `/api/cfb/fair-lines` | **200** honest empty · `slateStatus=not_connected` · `asOf=null` · `oddsAsOf=null` · `count=0` |
| mlb | `/api/mlb/fair-lines` | **200** proxy · empty → `no_slate` · never invent as-of |
| nba | `/api/nba/fair-lines` | **200** proxy · preserve upstream `slateStatus` / lines |
| nhl | `/api/nhl/fair-lines` | **200** proxy · offseason empty stays empty |
| wnba | `/api/wnba/fair-lines` | **200** proxy · preserve upstream status |
| ncaam/cbb | — | **Out** — no new API; desk copy stays not-connected |

Shared envelope (`apps/web/lib/fair-lines-api-board.ts`):

```ts
{
  sport: string;
  asOf: string | null;      // never Date.now()
  oddsAsOf: string | null;  // never Date.now()
  count: number;
  lines: unknown[];
  slateStatus: string;
  message: string;          // includes “we do not invent…” when empty
  modelVersion: string;
}
```

---

## DATA GAPs (follow-up only — do not invent)

| Gap | Why it blocks Lab / product | Notes |
| --- | --------------------------- | ----- |
| Historical odds warehouse | Lab bias / CLV need open→close series | See `docs/lab/*` · mark **N/A—DATA GAP** until owned |
| CFB model fair-lines | No `/cfb/fair-lines` on model-service | Season engine ≠ handicap KEI board |
| MLB/NBA/NHL/WNBA `as_of` / `odds_as_of` on model | Non-NFL boards omit book vintage stamps | Leave null until Odds join lands stamps |
| Odds API key rotation | Ops hygiene | Explicitly **out of scope** this overnight |
| Full multi-sport odds persist path | Training / CLV | Beat/worker owns NFL persist; do not write from subscriber GET |

---

## Code pointers

- NFL page-data: `apps/web/app/api/nfl/fair-lines/route.ts`
- Shared honesty envelope: `apps/web/lib/fair-lines-api-board.ts`
- Non-NFL page-data: `apps/web/app/api/{cfb,mlb,nba,nhl,wnba}/fair-lines/route.ts`
- Desk fail-closed copy: `apps/web/app/(pro)/pro/[sport]/fair-lines/page.tsx`
