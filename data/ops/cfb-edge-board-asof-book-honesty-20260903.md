# CFB Edge Board / Compare Odds — market as-of + book feed honesty (2026-09-03)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/cfb-edge-board-asof-honesty-715a`  
**Scope:** CFB Edge Board market as-of (stamp + stale) + Compare Odds carried vs not_carried for `americanfootball_ncaaf`.  
**Out of scope:** KEI recut, remat, mint, totals/spread calibrator, hide tiles, stake tags.

## A) Market as-of source (CFB)

| Layer | Behavior |
| --- | --- |
| Odds pull (`fetchEdgeBoard`) | Stamps per-row `linesAsOf` from The Odds API book/market `last_update` (second-resolution). Never invents fetch/GET clock. |
| Assemble (`/api/edge-board/cfb/assemble`) | `linesAsOf = resolveEdgeBoardBoardLinesAsOf(rows)` — latest sanitized row stamp. Blank → `null`. |
| UI (`EdgeBoardSportClient`) | Same NFL pattern: header `marketAsOfHeaderSuffix` + `MarketAsOfStamp` (`kind=lines`). Missing → **as-of unavailable** / **Market as-of unavailable**. Never bare `· ET`. |
| Stale | Same 6h policy (`MARKET_ASOF_STALE_MS`) → `· stale` when vintage is older. |

**Not used for CFB as-of:** request/render clock, fair-lines `board.asOf`, invent-now µs fingerprints.

When Odds API returns no NCAAF events (or omits `last_update`), assemble still returns `linesAsOf: null` and the board prints honest unavailable copy — Open/Best stay `—`, tiles stay visible.

## B) Compare Odds books — `americanfootball_ncaaf`

CFB **reuses** the NFL Odds API us/us2 inventory from PR #427 (`data/ops/nfl-compare-odds-book-feed-20260903.md`). Same provider gaps — do not invent Circa / Bet365 / Betr quotes.

**Carried (9 — requested):**  
`draftkings, fanduel, betmgm, betrivers, hardrockbet, fanatics, bovada, williamhill_us, betonlineag`

**Honest not_carried (3 — column only):**  
`bet365, circa, betr`

| Path | Change |
| --- | --- |
| `requestBooksForSport("cfb")` | Nine carried keys only |
| `cfbBookFeedStatus` / `bookFeedStatusForSport` | Same carried vs not_carried as NFL |
| Compare API `books[]` | `feedStatus: not_carried` for the three dead keys |
| UI | Existing “not on feed” chrome (no fake lines) |

**Regions:** `us,us2` (Hard Rock in us2).

## Evidence (code)

- Before: assemble hardcoded `linesAsOf: null`; client rendered `· ET` for non-NFL.
- After: CFB shares NFL as-of chrome; Odds rows carry book vintage when present.
- Before: CFB Compare Odds marked all twelve designated books `carried` and requested dead keys.
- After: same honesty bar as NFL Compare Odds.

## Tests

- `apps/web/__tests__/lib/cfb-edge-board-asof.test.ts`
- `apps/web/__tests__/lib/odds-api.test.ts` (CFB request + not_carried columns)
- `apps/web/__tests__/lib/odds-compare-payload.test.ts` (`bookFeedStatusForSport`)
