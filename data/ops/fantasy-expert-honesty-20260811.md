# Fantasy Expert Notes Honesty — 2026-08-11

## Problem

Fantasy desk expert blurbs led with lottery framing on fringe TEs:

- Gesicki-style: model #47 vs ADP ~268 (+221), **7.7 rec TDs**
- Engram / Parkinson: same pattern (~7 rec TDs, +170–200 ADP)

That was model-vs-ADP storytelling with inflated TE TD headlines — clickbait value board, not a desk.

## Fix (generator, not one-off patches)

**Generator:** `apps/web/lib/fantasy/expert.ts`  
Wired through `apps/web/lib/fantasy/enrich.ts` → every `expertBlurb` + Fantasy Expert section notes.

Rules:

1. **TE TD display caps** — only elite/TE1 with positional rank ≤5 may headline rec TDs; soft-cap display at 8. TE2/TE3 never headline ~6–7+ TDs; prefer yards/catches.
2. **ADP gap framing** — gaps ≥60 on TE (when model rank > early-round 36) or QB2 (pos rank ≥13) use “likes more than market / not a lottery smash” instead of “+N picks of value”.
3. **Preseason-fallback** — blurbs say “preseason sim” and append camp-season honesty so they don’t contradict the preseason banner.
4. Same path for `buildDrivers`, `buildExpertBlurb`, and `notableValueNotes`.

## Before / after (Gesicki-style)

| | Before | After |
|---|---|---|
| Drivers | `7.7 receiving TDs` | `620 receiving yards (~36/g)` / catches |
| Blurb lead | `… about 221 picks of value if the board stalls` | `… likes him more than market ADP ~268 — treat the gap as a signal, not a lottery smash` |
| Expert notes | `model #47 vs market ADP ~268 (+221). 7.7 receiving TDs.` | `preseason sim #47 likes him more than ADP ~268. 620 receiving yards…` |

Same pattern for Engram / Parkinson-style TE2/TE3 rows.

## Tests

```bash
cd apps/web && pnpm exec vitest run __tests__/lib/fantasy/expert.test.ts
```

Covers TE TD suppression, elite soft-cap, ADP soft-frame, and notableValueNotes for Gesicki/Engram/Parkinson-style inputs.

## Non-goals

No fantasy model retrain, K/DST invent, mock CPU, Edge Board, or KEI changes.
