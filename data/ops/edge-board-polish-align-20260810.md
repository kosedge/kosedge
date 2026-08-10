# Edge Board Polish — Banner + Align + Density — 2026-08-10

**Branch:** `feat/edge-board-polish-align` → `deploy-vercel`  
**Baseline tip:** #175 `84b5057f` (Week 1 stamp / Open+Current / kickoff stack)

## Owns / does not own

| Owns | Does not own |
|------|----------------|
| Hero/tab banner copy (short quiet line) | Tag formulas / thresholds |
| Overview + Stats horizontal baseline | Sim depth / new columns |
| Slight row density tighten (~8–16px) | Odds pipeline |

## Before → after

| Before | After |
|--------|--------|
| Multi-sentence Week 1 / Full slate intro under H1 | NFL hero banner removed |
| Long Methods paragraph under tabs | One quiet line + `title` tooltip for detail |
| Overview (Game col) / Stats (Kickoff col) drifted by content height | Shared baseline via `relative` cells + `pb-11` + absolute Overview/Stats controls |
| `py-6` row cells | `py-4` (+ minor header/card/mobile tighten) |

## Preserved (#173 / #174 / #175)

Week 1 / Full slate tabs · Open + Current · KEI / Edge / Action · Neutral · Melbourne · Tag policy · Stat Drop in-flow expand

## Smoke

1. `/edge-board/nfl` — no multi-sentence banner; quiet line under tabs  
2. Desktop: Overview + Stats share a baseline across ≥3 rows  
3. Week 1 still shows 13 when schedule pack has 13 REG W1 games  
4. Open Stats → next row pushed down cleanly (no overlay)  
5. Mobile: Overview/Stats side-by-side, cards still scannable  
