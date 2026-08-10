# Edge Board Density + Week 1 Tab + Open/Current Lines — 2026-08-10

**Branch:** `feat/edge-board-density-week1-lines` → `deploy-vercel`  
**Baseline tip:** #174 `9652991b` (layout tabs)

## Owns / does not own

| Owns | Does not own |
|------|----------------|
| Week 1 filter root-cause (schedule-pack week stamp) | Sim depth / kicker / mock CPU |
| Open vs Current semantics + immutability | New books / props |
| Kickoff stack + row density / Stat Drop in-flow | Path A3 |

## Week 1 empty — root cause + fix

### Root cause

Live Full slate showed REG Week 1 games (incl. SF–LAR Melbourne) **without** a `week` (or `seasonType`) field on assembled rows. The Week 1 tab uses `filterNflStrictWeekRows(rows, 1)`, which requires `row.week === 1`. Missing week ⇒ empty tab while the same games appear on Full slate.

Contributing factors:

1. Fair-lines payload often omits / nulls `week` on the Vercel→Railway path (row fields never serialized).
2. Matchup enrich resolved week for copy/Stat Drop (neutral table / context) but **did not write `week` back onto the row**.
3. `stampWeek1SeasonGates` ran **after** the Week 1 filter — too late to help classification.

### Fix

1. **Schedule pack stamp** (`apps/web/lib/nfl-edge-board-week.ts`) using the 2026 wall-chart REG schedule (same pack as the season wall chart). Runs **before** `filterNflStrictWeekRows` in assemble + page.
2. Enrich writes resolved `week` / `REG` back onto each row.
3. `rowWeek` coerces numeric strings (RSC/JSON).
4. PRE still excluded; Week 1 = all REG Week 1 schedule-pack games (Melbourne + domestic).

Default tab remains Week 1. Empty Week 1 only if the schedule pack truly has zero W1 matchups in the projection-backed board.

## Open vs Current

| Field | Source | Mutability |
|-------|--------|------------|
| **Open** | `open_spread_home` / `open_total` from first `odds_snapshots` capture (model-service fair-lines) | Immutable once set. Never invent `open = current`. |
| **Current** | Best-of-books / live consensus (`best_*` / Odds overlay) | Updates on odds refresh |

Web mapping (`fairLinesToEdgeBoardRows`):

- `row.open` ← first-capture open only (else omitted → UI `—`)
- `row.best` ← current (best book ?? market consensus)

`overlayOddsOntoFairLineRows` updates Current (`best` / book / juice) and **never** overwrites a set Open with Odds API “open” (that value is preferred-book current, not first capture).

### Refresh cadence

| Path | Cadence |
|------|---------|
| SSR page `/edge-board/nfl` | `force-dynamic`; fair-lines `cache: "no-store"` |
| Client soft refresh | `router.refresh()` every **6 hours** (`EDGE_BOARD_REFRESH_MS`) |
| `/api/edge-board/*/today` Redis/memory | **6h** TTL (`ODDS_CACHE_TTL_MS` / `s-maxage=21600`) |
| Stale hint | If `linesAsOf` / `odds_captured_at` older than 6h → show as-of (no live tick implication) |

Current moves without redeploy once Odds/fair-lines pull new snapshots. Open stays fixed after first capture lands in Postgres.

### Railway note

Model-service change: `_first_open_odds_by_game_ids` on fair-lines. Deploy Railway (`restore-working-ui` / model-service) for Open to populate from history. Until then Open shows `—` when history is missing; Current still updates from live books.

## Density / kickoff

- Kickoff stacks: date over time (+ ET)
- More vertical padding / clearer row borders
- Site label under team name; Stat Drop full-width in-flow (pushes next row)
- Book pills under Current prices
- Mobile: stacked kickoff; Stat Drop 2-column grid minimum

## Smoke checklist

- [ ] Week 1 tab non-empty with real W1 games (SF–LAR Melbourne + domestic)
- [ ] Week 1 count label matches visible game rows
- [ ] Date stacked over time
- [ ] Stats open does not cover next row
- [ ] Open ≠ Current when line has moved (sample game with snapshot history)
- [ ] Current updates after odds refresh (or next 6h client refresh / page reload)
- [ ] PRE never appears on Week 1
- [ ] Neutral · Melbourne preserved; Power on Stat Drop; PLAY = KEI vs market

## Tests

- `apps/web/__tests__/lib/nfl-edge-board-week.test.ts` — schedule stamp + Week 1 filter
- `apps/web/__tests__/lib/nfl-edge-board-from-fair-lines.test.ts` — open immutability / no invent

## Remaining gaps

1. Open stays `—` until Railway fair-lines ships first-snapshot fields + history exists for the game.
2. Fair-lines upstream `week` should still be fixed on Railway so web stamp is a safety net, not the only source.
3. Client refresh is 6h (Odds credit budget); shorter live tick would burn the free tier.
