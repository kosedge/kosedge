# NFL Edge Board / KEI Lines — kill invent-now as-of (2026-09-03)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-edge-board-asof-no-invent-f7bd`  
**Follow-up to:** PR #416 (merged) — **new PR, do not reopen 416**

## Live failure (Alex)

| Probe           | Result                                                                                       |
| --------------- | -------------------------------------------------------------------------------------------- |
| RSC MISS 23KB   | `data-missing=true` Market as-of unavailable (thin, no linesAsOf)                            |
| HTML MISS 319KB | `Lines as of Sep 2, 2026, 9:36 PM EDT` = request `2026-09-03T01:36:14Z` — **invented now()** |
| Fair-lines      | Header can print Sep 2 while model `odds_as_of` is Aug 21                                    |

Compare Odds held still — leave it. Props PASS after #419 — leave it.

## Fix

| Layer                           | Change                                                                                         |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| `routes/nfl.py`                 | `odds_as_of` / `as_of` = Odds API `last_update` or stored capture — **never** `datetime.now()` |
| Per-row `odds_captured_at`      | Prefer event `last_update`                                                                     |
| `tasks.py` persist              | Skip books with no `last_update` (no invent `_now_utc()`)                                      |
| Web `resolveEdgeBoardLinesAsOf` | Market capture only; ignore `boardAsOf`                                                        |
| `sanitizeMarketCaptureIso`      | Strip near-now µs invent fingerprints from HTML rows/header                                    |
| Fair-lines / Edges UI           | Stamp **model `oddsAsOf` only** (Aug 21), not render time / row max                            |

Blank / invent → `Market as-of unavailable`.

## Tests

- `nfl-edge-board-asof-no-invent.test.ts` — blank + invent → unavailable
- `market-asof-stamp.test.ts` — sanitize invent clocks
- `test_nfl_fair_lines_odds_asof.py` + snapshot `odds_as_of` assert
