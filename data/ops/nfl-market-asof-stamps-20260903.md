# NFL market as-of / stale stamps — 2026-09-03

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-market-asof-stamps-f7bd`  
**Enterprise leftover:** GPT 6.2 #6

## Goal

Every NFL market table a paying subscriber uses must show an **honest** as-of / stale stamp. Do not invent freshness.

## Surfaces

| Surface                    | Stamp                                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------- |
| Compare Odds (`/odds/nfl`) | `Odds as of …` + books with `last_update`; **unavailable** when Odds API omits stamps        |
| Edge Board                 | Board + per-row Lines as of (always when present; amber · stale >6h); unavailable when blank |
| KEI Lines                  | Lines as of from `oddsAsOf` / `asOf` + diagnostics bookmakers                                |
| Edges desk                 | Market as of from fair-lines (then props `updatedAt`) + books                                |
| Props board                | Board as of from max `updatedAt` — **no** editorial `KOSEDGE_DATE` fallback                  |
| Game Boxes                 | No change — model means only, no book market numbers                                         |

## Honesty rules

- Stamp the market actually pulled (book labels + source timestamp).
- Blank / missing upstream → `Market as-of unavailable` — never mint `Date.now()` or editorial dates as market as-of.
- `resolveEdgeBoardLinesAsOf` no longer falls back to wall clock when both market and board stamps are missing.
- Compare Odds cache bump `v6` carries `asOf` / `bookAsOf` (not fetch time as market as-of).

## Out of scope

- No KEI mint, remat, tile hide, paywall, DFS/Guillotine.
- Does not reopen ATD / Bijan / Mock / Overview catalog (PRs 410–414).

## Tests

- `__tests__/lib/market-asof-stamp.test.ts`
- `__tests__/lib/nfl-market-asof-surfaces.test.ts` (Compare Odds + other tables)
- `__tests__/lib/odds-api.test.ts` (last_update plumbing; blank → null)
- `__tests__/lib/nfl-week1-desk-agreement.test.ts` (no invent-now as-of)
