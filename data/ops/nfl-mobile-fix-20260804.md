# NFL mobile touch fix — 2026-08-04

## Surfaces
- `/pro/nfl/survivor?mode=planner` (Survivor Planner)
- `/pro/nfl/survivor` (helper tab)
- `/pro/nfl/game-boxes`
- `/pro/nfl/model`
- Shared Pro sport / desk nav (`SportProHeader`, `sport-pro-nav`)

## What was broken (reproduced at 390×844)
1. **Sticky header ate taps** — Pro header ~125px tall on mobile; when week chips / Clear sat under it, `elementFromPoint` hit the desk nav, so taps looked “dead”.
2. **Tiny touch targets** — planner recommendation chips `min-h-9` (~36px); sport + desk nav `text-xs` / `py-1`–`py-1.5`.
3. **Season tools buried** — Survivor / Game Boxes / Season Model only under Overview “More tools”, hard to reach one-handed.
4. **Planner layout** — path survival scrolled off-screen; week pick `<select>` capped width; Clear/reset cramped on narrow widths.
5. **User menu backdrop** shared `z-40` with sticky header (could trap taps while open).

## What we fixed
- Compact sticky header: single-row sport scroll, ~44px desk/sport targets, CSS var `--kos-pro-header-h`.
- `scroll-padding-top` + `touch-action: manipulation` on document; InstantFilterBar sticks to header var.
- Planner: sticky path-survival strip, full-width selects/Clear/Reset on small screens, 2-col ≥44px chips, week `scroll-mt` clears header+strip.
- Mode tabs full-width ≥44px; helper used-team chips ≥44px; Game Boxes project CTA full-width on mobile.
- Promote Survivor / Game Boxes / Season Model onto NFL primary desk nav.
- UserMenu overlay above sticky header (`z-50` / `z-[60]`).

## Manual verification
- Production (pre-fix): SEA chip lock updated URL/`Used`, path survival → 62.4%; sticky overlay confirmed on Clear.
- Game Boxes: Project box scores entered Simulating… at mobile viewport.
- Local/post-deploy: re-check planner pick → lock → path survival sticky while scrolling; Clear/Reset; mode tabs; desk nav Survivor link.

## Remaining
- Game Boxes result tables still horizontal-scroll (acceptable for dense stats).
- Freshness banner still tall when degraded (pushes content; not a tap blocker).
- Full hamburger IA not added — horizontal scroll desk nav only.
- Real-device Safari/Chrome pass still recommended after Vercel deploy.
