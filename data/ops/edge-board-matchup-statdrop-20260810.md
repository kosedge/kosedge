# Edge Board Matchup Overviews + Stat Drop — 2026-08-10

**Branch:** `feat/edge-board-matchup-statdrop` → `deploy-vercel`  
**Baseline tip:** truth-layer `a5c4b5f7` (#171)

## Owns / does not own

| Owns | Does not own |
|------|----------------|
| Matchup overview copy engine | Fantasy mock CPU |
| Stat Drop schema + UI | Team preview markdown |
| Season / neutral gates | Sim depth bump / props / Path A3 |
| Desk voice rotation (no bylines) | New model layers |

## Problems fixed

1. Overviews sounded the same (generic pros/cons picker).
2. “Recent turnovers” / recent form on Week 1 — invalid.
3. Neutral-site games written like normal home games.
4. Stat Drop empty / Stats ▾ disabled — now wired.
5. Copy not useful before risking money — now Bottom line / What matters / Watch with real numbers.

## Contract (preserved)

- **PLAY / desk tags** = KEI vs market only (truth-layer).
- Decision Engine action labels remain Model fair vs market (labeled separately).
- Missing data → em dash / omit. Never invent form.

## Overview structure (every game)

1. **Bottom line** — 1–2 sentences with an actual number/angle  
2. **What matters** — 2–4 bullets that move this spread/total/ML  
3. **Watch** — 1 line that flips the view  

Ban: interchangeable openers, “both teams will try to score,” same three factors every card.

## Season gates (hard)

| Situation | Rule |
|-----------|------|
| Week 1 / no prior games | Forbidden: recent turnovers, last-3 form, hot/cold. Use roster/OL-DL/QB, rest/travel, neutral, market number |
| Games 2–4 | Light real evidence only; structural-heavy |
| Midseason+ | Form OK if labeled and data exists |
| Missing data | Omit |

Implemented in `apps/web/lib/edge-board-season-gates.ts`.

## Neutral site

- Static 2026 international table (`apps/web/lib/nfl-neutral-sites-2026.ts`)
- Copy + Stat Drop say Neutral + city; HFA 0 (or partial clause if ever non-zero)
- No “home crowd” for nominal home on neutral sites
- Card title uses `vs` instead of `@` when neutral

## Desk voices

5 lenses, stable `hash(game_id)` → same voice on refresh:  
`structural` · `market` · `script_pace` · `dog` · `totals`  
No personal bylines on Edge Board cards.

## Stat Drop (uniform, never empty section)

Slots (always 8; missing → `—`; Power required when KEI exists):

1. Power (model E[wins] + KEI relative pts + Δ)  
2. Spread: market vs KEI  
3. Total: market vs KEI  
4. Implied WP both sides  
5. Site: Home/Road/Neutral + HFA pts  
6. Rest (days / bye / season open)  
7. Pace proxy  
8. One structural tag per side (packaged efficiency priors)

## Before / after samples

### Before (legacy `generateGameOverview`)

```
New England Patriots travels to face Seattle Seahawks in a matchup likely to turn on a few high-leverage variables. Both teams enter with clear strengths and controllable vulnerabilities.

New England Patriots — Pros: Strong recent efficiency trend… Cons: Recent turnover and penalty profile has spiked…

Seattle Seahawks — Pros: Home environment has produced stronger baseline execution… Cons: Possession-management consistency has dipped in recent samples…
```

Problems: interchangeable opener, Week-1 illegal “recent” language, home-crowd framing, no numbers, no Stat Drop.

### After — Week-1 style (NE @ SEA, voice `script_pace`)

```
Bottom line
Patriots at Seahawks: Pace proxy Patriots 0.97 / Seahawks 0.96 — mid-pack pace; KEI total 41.5 vs market 44.5.

What matters
• Pace proxy Patriots 0.97 / Seahawks 0.96 → mid-pack pace
• Total: KEI 41.5 vs market 44.5 · under
• Patriots tag: … (prior efficiency — not in-season form)
• Spread: KEI -3.5 ≈ market -3.0 — no forced lean

Watch
If early downs stall, the under script was the real bet — not the side.

Early-season uncertainty: no trailing sample yet — this is structure + price only.
```

**Stat Drop (excerpt):** Power shows both sides + Δ; Rest = Season open; no recent-form slots.

### After — Neutral (SF vs LAR, Melbourne, voice `dog`)

```
Bottom line
49ers vs Rams in Melbourne: dog 49ers is priced fairly vs KEI — no gift on the plus side. Neutral site in Melbourne — no home-crowd edge for the nominal home side.

What matters
• Neutral site in Melbourne — no home-crowd edge for the nominal home side
• Spread: KEI -2.5 ≈ market -2.5 — no forced lean
• Implied WP …
• … model power …

Watch
If the board still prices a full home-crowd HFA, the number is lying about the site.
```

**Stat Drop site:** `Neutral · Melbourne · Melbourne Cricket Ground · HFA 0`

## Wire points

| Piece | Path |
|-------|------|
| Season gates | `apps/web/lib/edge-board-season-gates.ts` |
| Desk voices | `apps/web/lib/edge-board-desk-voices.ts` |
| Neutral 2026 | `apps/web/lib/nfl-neutral-sites-2026.ts` |
| Context + KEI power | `apps/web/lib/edge-board-matchup-context.ts` |
| Overview engine | `apps/web/lib/edge-board-matchup-overview.ts` |
| Stat Drop schema | `apps/web/lib/edge-board-stat-drop.ts` |
| Enrich on assemble | `apps/web/lib/edge-board-matchup-enrich.ts` + `build-edge-board-rows.ts` |
| UI | `EdgeBoard.tsx` + `EdgeBoardStatDrop.tsx` |
| Tests | `apps/web/__tests__/lib/edge-board-matchup-overview.test.ts` |

## Honesty

- KEI ≈ market → say so; don’t force a lean  
- Early season → uncertainty clause  
- PLAY still KEI vs market only  

## Remaining gaps

1. Rest days / bye not yet joined from DB context tables (Week 1 correctly shows “Season open” when week stamps).  
2. Fair-lines `week` can be null in some pulls — live assembler stamps `currentWeek` + commence window; prefer fixing upstream week join.  
3. True PR live fetch not required — launch E[wins] power map used when available; else KEI proxy.  
4. Structural tags are packaged prior-season efficiency, not live injury/QB situation feeds.  
5. Non-NFL sports get structured template via context builder but not full NFL enrichment.  
6. Implied WP empty when fair-lines omit win probs on the board row.

## Test plan

- [x] Unit: season gates, voice stability, Stat Drop schema, Week-1 form ban, Melbourne neutral  
- [ ] Manual: `/edge-board/nfl` mobile + desktop — open 3 cards, confirm distinct copy + Power on every Stat Drop  
- [ ] Confirm no personal bylines; PLAY tags unchanged vs truth-layer  
