# NFL market payload + SSR waterfall — 2026-09-03

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-odds-fat-payload-b6cd`  
**Diagnosis:** Alex (NFL model engineer) live GET — use this; do not invent another theory.

## Live evidence (Alex)

| Surface | What Alex measured | Cause |
| --- | --- | --- |
| `/odds/nfl` | **2,351,253 bytes** in ~0.8–1.1s; Web RSC **~22,330** children + `className` nodes | Table exploded into React elements. **NOT model JSON.** |
| `/edge-board/nfl`, `/pro/nfl/edges`, `/pro/nfl/fair-lines` | **9.8–12.5s** for **23–116KB** HTML | **SSR wait on model-service**, not download. |
| Railway `GET /nfl/props/board?season=2026&week=1&limit=50` | **577ms / 78KB** | API is fine — page waterfall was the bug. |

Agent re-check (www, same day): odds ~4.6MB / ~22,281 `className`; edge-board/edges/fair-lines ~38–169KB with total ~12–13s while TTFB ~0.5–1.5s (stream held open on SSR data).

## Fix

### Compare Odds — stop shipping ~22k className nodes

1. `/odds/[sport]` SSR shell only; `OddsCompareBoard` client-fetches `/api/odds/{sport}/compare`
2. Slim unused book fields (`slimOddsComparisonForBoard`, cache `v7`)
3. Keep PR 416 as-of stamps after fetch

### Edge Board / Edges / Fair-lines — don’t block HTML on serial SSR waits

1. Pages parse params/filters only (Edge Board `Promise.all([params, searchParams])`)
2. Client-fetch page-data APIs:
   - `/api/edge-board/[sport]/assemble`
   - `/api/nfl/edges-desk` (desk already `Promise.all` fair-lines ∥ edges/today ∥ props/board)
   - `/api/nfl/fair-lines`
3. Document HTML completes without waiting on model-service; boards + as-of fill client-side

## Out of scope

Hide tiles, mint KEI, remat, paywall, ATD/Bijan/Mock/Guillotine/KEI stub/props header (419)/Awards-Depth, product redesign.

## Tests

- `__tests__/lib/odds-compare-payload.test.ts`
- `__tests__/lib/nfl-market-waterfall-payload.test.ts` — shells don’t await model-service; APIs + as-of wired
- Existing as-of + odds-api + KEI Lines href contracts
