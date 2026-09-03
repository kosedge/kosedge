# NFL market as-of / stale stamps — 2026-09-03

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-market-asof-stamps-f7bd`  
**Enterprise leftover:** GPT 6.2 #6  
**Live audit (www after PR 414):** orphan `· ET` headers with no market vintage

## Goal

Every NFL market table a paying subscriber uses must show an **honest** as-of / stale stamp **in the header chrome**. Do not invent freshness.

## Live bugs hit

| Surface               | Was                                                  | Fix                                                    |
| --------------------- | ---------------------------------------------------- | ------------------------------------------------------ |
| `/odds/nfl`           | `NFL · Market research · ET` (datetime missing)      | Header → `· as of …` or `· as-of unavailable`          |
| `/edge-board/nfl`     | `NFL · KEI vs Market · KEINFL · ET`                  | Same header suffix from `linesAsOf`                    |
| `/pro/nfl/edges`      | `Week 1 · 2026` only (as-of count 0)                 | Chip + table title include header suffix               |
| `/pro/nfl/fair-lines` | Kickoffs look like vintage; `· ET` after already-EDT | Chip gets line as-of; drop redundant `· ET` on kickoff |

## Honesty rules

- Stamp the market actually pulled (book labels + source timestamp).
- Blank / missing upstream → `as-of unavailable` / `Market as-of unavailable` — never mint `Date.now()` or editorial dates.
- `fetchNflFairLines` no longer invents `asOf` with `new Date().toISOString()` when API omits `as_of`.
- `resolveEdgeBoardLinesAsOf` no longer falls back to wall clock when both market and board stamps are missing.
- Compare Odds cache bump `v6` carries `asOf` / `bookAsOf` (not fetch time as market as-of).
- Kickoff strings (`formatKickoff`) are **game time**, not line vintage — do not treat them as as-of.

## Out of scope

- `/pro/kei-lines/nfl` stub, Guillotine destination, Awards/Depth (PR 415), remat, paywall, KEI mint, tile hide.

## Tests

- `__tests__/lib/market-asof-stamp.test.ts` — header suffix + blank → unavailable
- `__tests__/lib/nfl-market-asof-surfaces.test.ts` — Compare Odds + other tables
- `__tests__/lib/odds-api.test.ts` — `last_update` plumbing; blank → null
- `__tests__/lib/nfl-week1-desk-agreement.test.ts` — no invent-now as-of
