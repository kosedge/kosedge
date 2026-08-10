# Edge Board Matchup Overview + Stat Drop Overhaul

**Date:** 2026-08-09  
**Branch:** `cursor/edge-board-matchup-statdrop-cc43` → `deploy-vercel`  
**Scope:** Edge Board matchup preview copy + uniform Stat Drop (NFL priority; shared components for MLB / other sports)

## Problems killed

1. Interchangeable template sludge (“travels to face…”, generic pros/cons)
2. Fake “recent form / recent turnovers” on Week 1 / first game
3. Neutral-site games written like normal home/away
4. Empty Stats ▾ stub wasting real estate
5. Copy that no bettor would read before risking money

## What shipped

| Deliverable | Location |
|-------------|----------|
| Overview generator (Bottom line / What matters / Watch) | `apps/web/lib/edge-board-matchup-overview.ts` |
| Desk voice rotation (stable hash of `game_id`) | same — Structural / Market / Script / Dog / Totals |
| Uniform Stat Drop schema (8 slots, em dash when missing) | `apps/web/lib/edge-board-stat-drop.ts` |
| Stat Drop UI (mobile + desktop expander) | `apps/web/components/edge-board/StatDropPanel.tsx` + `EdgeBoard.tsx` |
| Schedule context on fair-lines (neutral, venue, rest, unit indexes) | `services/model-service/src/routes/nfl.py` → web fair-lines types |
| Unit tags from offense/defense indexes | `apps/web/lib/edge-board-unit-tags.ts` |
| Tests | `apps/web/__tests__/lib/edge-board-matchup-overview.test.ts` |

## Rules (ops summary)

### Season gates

| Situation | Copy rule |
|-----------|-----------|
| Week 1 / PRE / no prior games | Forbidden: recent turnovers, last-3 form, “hot offense.” Use roster/OL/QB/schedule/market/rest/neutral. |
| Games 2–4 | Light prior-game evidence only if real; still heavy on structure. |
| Midseason+ | Form OK only when labeled and real — we still do not invent it. |
| Missing data | Say nothing / show `—`. |

### Neutral site

- Detect from `nfl_game_context.venue.neutral_site` or city hints (London, Mexico City, etc.).
- Copy + Stat Drop must say Neutral (city when known).
- HFA display = 0 (or reduced if model supplies partial).
- No “home crowd” / “defend home turf” for the listed host.

### Voices

- Desk labels only (`Market desk`, …). **No personal bylines** on Edge Board cards.
- Same `game_id` → same voice on refresh.

### Stat Drop slots (NFL order)

1. Power (KEI) · 2. Spread / KEI · 3. Total / KEI · 4. Implied WP  
5. HFA / site · 6. Rest · 7. Pace / plays · 8. Units to watch  

MLB labels swap in park / starter / bullpen analogs. Section always visible.

### Explicit non-goals (honored)

- No Path A / season-engine math changes  
- No prop engine  
- No Decision Engine PLAY spam in overview (Action column owns labels)  
- No long articles / writer personal bylines  

## Before / after samples

### Sample A — Week 1 home/away (BUF @ KC)

**Before (old template sludge):**
> Buffalo Bills travels to face Kansas City Chiefs in a matchup likely to turn on a few high-leverage variables. Both teams enter with clear strengths…  
> Buffalo Bills — Pros: Strong recent efficiency… Cons: Recent turnover and penalty profile has spiked…  
> Kansas City Chiefs — Pros: Home environment has produced stronger baseline… Cons: Possession-management consistency has dipped in recent samples…

**After (Structural desk — KEI ≈ market, honest no-lean):**
```
BOTTOM LINE
KEI sits near the market — no forced lean from the number alone. Early-season sample is thin — price structure, not invented form.

WHAT MATTERS
• Bills: Explosive skill · Chiefs: Elite pass rush.
• Implied WP (KEI): Bills 39% · Chiefs 61%.

WATCH
Watch: confirmed starters / OL availability — first-game form claims are noise.

Structural desk
```

**Stat Drop:** Power `Chiefs −3.5` · Spread `-3 / -3.5` · Total `47.5 / 46.0` · WP `39% · 61%` · HFA `Home · 2.0` · Rest `7d · 7d` · Pace `—` · Units `Explosive skill · Elite pass rush`

### Sample B — Neutral London (JAX @ CHI listed)

**Before:** “travels to face” + “Home environment…” sludge.

**After (Script desk):**
```
BOTTOM LINE
Neutral site (London): pace/script edges matter more than crowd noise. … Model uses zero / reduced neutral HFA.

WHAT MATTERS
• Neutral · London — do not price a full home-crowd bump for Bears.
• …

WATCH
Watch: travel/rest + any late inactive that rewrites the reduced-HFA script at Neutral · London.

Script desk
```

**Stat Drop site cell:** `Neutral · London · HFA 0.0` (highlighted)

### Sample C — Midseason PHI @ DAL (Market desk)

Different voice + rest edge + key-number cross — not copy-paste of Week 1 card.

## Smoke checklist

- [ ] Week-1-style REG card: no “recent turnovers”
- [ ] Neutral card (if on slate / fixture): Neutral in overview + Stat Drop
- [ ] Normal home/away: Power + Spread/Total/WP populated when KEI present
- [ ] Three different games → different desk voices / bullets (not copy-paste)
- [ ] Mobile: Stat Drop grid readable under overview
- [ ] Action column still sole PLAY surface

## Deploy notes

- Web: Vercel auto-deploy from PR → `deploy-vercel`
- Model-service: Railway deploy needed for fair-lines context fields (`neutral_site`, rest, unit indexes). Without Railway deploy, web still renders Stat Drop from KEI/market/WP with `—` for rest/units/neutral until context lands.
