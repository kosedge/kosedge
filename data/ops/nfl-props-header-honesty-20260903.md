# NFL Props header honesty — Preseason vs Week 1 REG — 2026-09-03

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-props-header-honesty-1676`  
**Enterprise leftover:** NFL P1 after PR 416 as-of stamps  
**Live audit (www):** `/pro/nfl/props` showed `Date: August 11, 2026 · 2026 Preseason` while Edge Board said `Week 1 REG`, with a separate real `Board as of Sep 2…`.

## Goal

Header chrome on the weekly props board must agree with the spine week and with Edge Board. Keep a real board as-of when present. Do not invent freshness from editorial launch dates or kickoff times.

## Live bugs hit

| Surface           | Was                                                                 | Fix                                                                 |
| ----------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `/pro/nfl/props`  | Period = calendar `Preseason` via `formatNflWeekLabel` (cutoff Sep 7) while board week = 1 REG | Period = `2026 · Week 1 REG` via `formatNflPropsBoardPeriod`        |
| `/pro/nfl/props`  | Dual dates: editorial `Date: August 11, 2026` + real Board as-of   | Drop `KOSEDGE_DATE`; keep PR 416 `MarketAsOfStamp` board as-of only |

## Honesty rules

- Spine / requested week drives the period label. Week 1 REG props must not read Preseason when Edge Board says Week 1 REG.
- `Preseason` only when season type is explicitly PRE.
- Board as-of = max row `updated_at` (model/board vintage). Blank → `Market as-of unavailable` — never August 11 editorial fallback.
- Kickoff / game time is **not** line vintage.

## Out of scope

- KEI mint, remat, tile hide, paywall, ATD/Bijan/Mock/Overview/Guillotine, KEI stub redirect (418 in flight).

## Tests

- `__tests__/lib/nfl-props-header.test.ts` — Preseason vs Week 1 REG; page wiring
- `__tests__/lib/nfl-market-asof-surfaces.test.ts` — props page drops August 11 dual Date
