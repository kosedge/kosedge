# Fantasy Draft Rank Board — KosEdge take order (not ADP-delta default)

**Date:** 2026-08-22  
**Branch:** `cursor/fantasy-draft-rank-board-4b71` → `deploy-vercel`  
**Priority:** P0 Fantasy product identity (post-#284)

## Problem

#284 defaulted the desk to **Value Δ vs ADP** — a bargain-hunter sort. Product intent is a **KosEdge recommended draft order (1…N)** from the same season projections, with ADP as reach/fall discipline only.

## Product contract (shipped)

| Item | Behavior |
|------|----------|
| Default tab | **Draft rank** (KosEdge take order) |
| Default format | **PPR** (`?scoring=` absent → `ppr`) |
| Sort | `deskOrder` 1…N from `applyDeskRankPolicy` |
| Model rank | Secondary tab — raw projection points order |
| Value / ADP | Tertiary tab — gap sort, not default |
| Columns (draft tab) | Draft · Model · Player · Pos · Team · Med · ADP · vs ADP · Advice · Floor · Ceil · Schedule |
| Methods line | “Rank = our projections; ADP limits extreme reaches/falls. Default format PPR.” |

No new projection engine. K/DST publish path unchanged.

## Formula (plain English)

Start from **Model rank** (`rankOverall` = season fantasy points sort on the weekly spine SUM).

For players with **high-confidence same-format ADP**:

1. **Reach penalty** — if model wants a player more than one round (12 picks) earlier than ADP, push them down:  
   `+ (ADP − modelRank − 12) × 0.85` board-key slots (QB gets extra suppress after 24 picks ahead).
2. **Wait bubble** — if ADP is ahead of model (market favorite), bubble up modestly:  
   `− min(modelRank − ADP, 24) × 0.35` slots.
3. Sort by that **board key** ascending → assign **Draft rank** 1…N.

Unmatched or cross-format ADP → draft rank = model rank (no invented blend).

Implementation: `apps/web/lib/fantasy/desk-rank-policy.ts`, applied in `load-desk.ts` after enrichment.

## Five example moves (fixture smoke)

| Player | Model | ADP | Draft | Move vs pure model |
|--------|-------|-----|-------|---------------------|
| CMC | 1 | 3 | 1 | Stays near top — ADP close |
| Ja'Marr Chase | 2 | 2 | 2 | Locked with market |
| Jahmyr Gibbs | 5 | 8 | 3 | Bubbles up (ADP later than model) |
| Josh Allen | 3 | 28 | 4 | Pushed down (QB reach vs ADP) |
| Zach Charbonnet | 4 | 120 | 5 | Heavy reach penalty |

Pure ADP would never rank Charbonnet #4; pure model leaves Allen #3. Draft rank is the disciplined middle.

## Smell checklist

| # | Check | Pass |
|---|--------|------|
| 1 | First load sorted Draft rank 1…N | ✅ `initialTab="draft"` + `deskOrder` sort |
| 2 | Default format PPR | ✅ fantasy routes + profile order |
| 3 | Reach nudged / badged | ✅ desk policy + `valueLabel` vs ADP column |
| 4 | STD / Half / PPR toggles | ✅ unchanged query links |
| 5 | K/DST on board | ✅ unchanged merge path |

## Tests

- `apps/web/__tests__/lib/fantasy/desk-rank-policy.test.ts`
- `apps/web/__tests__/lib/fantasy/fantasy-draft-rank-board-smoke.test.ts`

## Live smoke (manual)

1. Open `/pro/nfl/fantasy` — no query → **PPR** active, **Draft rank** tab selected.
2. Top row Draft #1 should be highest board-key player (typically elite RB/WR).
3. Toggle Half / Standard — board reloads, draft sort preserved.
4. **Model rank** tab — order differs where ADP guardrails moved players.
5. **Value / ADP** tab — gap sort; not the landing default.

## Deploy

Web-only (Vercel). No Railway rematerialize required.
