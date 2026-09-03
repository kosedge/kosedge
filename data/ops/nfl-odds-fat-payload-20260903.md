# NFL Compare Odds fat payload — 2026-09-03

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-odds-fat-payload-b6cd`  
**Enterprise leftover:** paying-subscriber download hang on market surfaces

## Live bug

| Surface | Evidence (www, 2026-09-03) | Cause |
| --- | --- | --- |
| `/odds/nfl` | **~4.6MB** document HTML; TTFB ~0.1–1.5s | SSR inlined ~272 games × 9 books × 3 markets as React HTML cells |
| `/api/odds/nfl/compare` | **~183KB** JSON (same data) | Already cached; page was re-hydrating it into multi-MB markup |
| `/edge-board/nfl`, `/pro/nfl/edges` | ~190–320KB HTML; slow full download in some audits | Not multi-MB; out of this PR’s inlining fix (no product redesign) |

## Fix

1. **SSR shell only** on `/odds/[sport]` — chrome + `OddsCompareBoard` client island.
2. **Client-fetch** `/api/odds/{sport}/compare` for the table (same board UI: mobile cards + desktop multi-book table).
3. **Slim wire rows** via `slimOddsComparisonForBoard` — drop unused `commenceTime`, home spread/juice, under juice, numeric point mirrors, ML price mirrors. Cache key bump `v6` → `v7`.
4. **Keep as-of stamps** from PR 416 — header `· as of …` / `as-of unavailable` + `MarketAsOfStamp` after the compare payload returns (loading shows `…`).

## Out of scope

- Hide tiles, mint KEI, remat, paywall
- ATD / Bijan / Mock / Guillotine / KEI stub / props header (419) / Awards/Depth
- Redesign Edge Board or Edges desk

## Tests

- `__tests__/lib/odds-compare-payload.test.ts` — slim fields; page does not SSR rows; board client-fetches; API uses v7 slim
- Existing as-of + KEI Lines href contracts still green
