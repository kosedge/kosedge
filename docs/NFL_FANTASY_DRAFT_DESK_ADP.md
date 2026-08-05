# Fantasy Draft Desk — Real ADP Integration

Replaces the Phase 1 KosEdge ADP **proxy** with FantasyPros consensus market ADP
so **Model vs ADP** is a real draft-market edge signal.

## Source

| Item | Detail |
| --- | --- |
| Provider | FantasyPros partners consensus rankings API |
| Endpoint | `https://partners.fantasypros.com/api/v1/consensus-rankings.php` |
| Sport / type | `NFL`, `type=ADP`, `week=0` (season-long) |
| Format map | Standard → `STD`, Half-PPR → `HALF`, PPR → `PPR` |
| ADP field | `rank_ave` (average draft position) |
| Freshness | `last_updated` / `last_updated_ts` from the feed |
| Attribution | ADP data from FantasyPros |

Live fetch revalidates about hourly (`next.revalidate = 3600`). If the live
call fails, the desk falls back to checked-in snapshots under
`apps/web/data/fantasy/adp-fantasypros-2026-{standard,half_ppr,ppr}.json`.

Refresh snapshots:

```bash
node scripts/nfl/refresh-fantasypros-adp.mjs 2026
```

## Enrichment

1. Load draft rankings (model-service or preseason fallback).
2. Fetch FantasyPros ADP for the active scoring profile.
3. Match players (sportsdata id → full name → short name → initial+last+team+pos → unique last+team+pos).
4. Set `adp` / `valueDelta` only on clean matches; otherwise `null` (UI shows —).
5. Value board sorts by `valueDelta = ADP − modelRank` and **excludes** unmatched rows.

## Transparency on the desk

Hero line shows:

- ADP source label (FantasyPros consensus ADP)
- Freshness (`updated M/D` · live cache | snapshot)
- Match coverage (`matched N/total`)

Methods panel lists feed limitations (platform mix, expert panel size, hourly
cache, unmatched → —).

## Limitations (honest)

- FantasyPros aggregates multiple platforms/experts — not a single draft room.
- Panel size / filters vary by feed response (`total_experts`, `filters`).
- Name matching can miss obscure / deeply abbreviated / team-mismatch rows; we
  do **not** invent ADP for those.
- Official FantasyPros commercial API (v2 + API key) is not wired; partners
  feed is the reviewable integration used here.
- K/DST appear when present in the same ADP feed; preseason fallback boards
  still omit K/DST from model rows.

## Before / after (Half-PPR examples)

**Before (proxy):** ADP was derived from model rank + positional jitter.
“Value” was mostly model-vs-model — e.g. a mid QB looked like a mild value
because the proxy pushed QBs later by a fixed offset, not because the market
disagreed.

**After (FantasyPros market ADP):** same model board, real `rank_ave`:

| Player (example shape) | Model rank | Proxy behavior | Market ADP | Value Δ (market) | Read |
| --- | ---: | --- | ---: | ---: | --- |
| Early feature RB market loves | mid/late on cool model | “fair / mild reach” (proxy hugged model) | ~top 5–15 | large negative | Real reach — market price is expensive vs model |
| Model-loved QB, market waits | top ~20–40 | small synthetic “value” | ~160–250 | large positive | Real wait-on-QB signal — actionable as *don’t pay early* |
| Skill-position sleeper | model earlier than crowd | noisy / muted | later ADP | clear positive | True value-board candidate |

Exact names move with each preseason sim + weekly ADP refresh; the desk always
shows current source/freshness so the signal stays auditable.

## Key files

- `apps/web/lib/fantasy/adp-fantasypros.ts` — fetch + snapshot
- `apps/web/lib/fantasy/adp-match.ts` — name/team matching
- `apps/web/lib/fantasy/enrich.ts` — attach ADP / value Δ
- `apps/web/lib/fantasy/load-desk.ts` — desk loader
- `apps/web/data/fantasy/adp-fantasypros-2026-*.json` — offline snapshots
- `scripts/nfl/refresh-fantasypros-adp.mjs` — snapshot refresh

## Out of scope (this pass)

- Phase 2 multi-team mock draft room
- Major new ranking columns
- Separate Sleeper/Yahoo ADP merges (single reliable feed first)
