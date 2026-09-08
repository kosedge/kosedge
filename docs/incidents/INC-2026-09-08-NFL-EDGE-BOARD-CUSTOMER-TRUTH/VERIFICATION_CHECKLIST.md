# Verification checklist — INC-2026-09-08 NFL Edge Board customer-truth

**CoS merge authority: FAILED** until Ryan ACCEPT after independent verify below.  
PR stays open — do **not** merge on agent green alone.

## Product Engineer (independent)

- [ ] `/pro/nfl/edges` — no green **negative** selected-side edge on any spread/total/ML row
- [ ] ARI @ LAC (or current equivalent): Fair / Book / Edge either **arithmetically reconcile** (same market identity as edge calc) **or** edge chrome is absent (`DATA GAP` / omitted) — never Fair −8.31 · Book −9.50 · Edge +1.7
- [ ] BAL / NYJ class: Side Home shows **positive** magnitude (e.g. `+1.7 pts`), not `-1.7 pts`
- [ ] `/edge-board/nfl` Action Fair · Mkt · Edge triples reconcile on every spread/total row; mismatch → no Edge paint
- [ ] Spot-check `/edge-board/{cfb,nba,nhl,mlb,wnba}` — no negative `edgeMagnitude`; no Fair/Mkt/Edge disagreement when all three present
- [ ] Confirm ML / totals still use **their own** formulas (prob pp / total points) — not blind abs(spread) misuse
- [ ] No PLAY / LEAN / PASS threshold or KEI fair changes in the diff

## Riley Nash (Editor — independent fact gate)

- [ ] Hard-number pass on NFL Week 1 desk + Edge Board Action cells for ARI@LAC, BAL@IND, NYJ@TEN
- [ ] Confirm displayed Book/Mkt is the line used for the painted edge (stake/compare identity)
- [ ] Confirm selected-side copy never implies “negative edge” as a bad Home lean
- [ ] Kick back invents nothing — forward-only from this lock; cite incident receipt

## CI / agent

- [ ] `apps/web` vitest: `edge-board-customer-truth`, desk confidence, mlb edges, edge-board-side, edge-action-smoke, nfl-edge-board-from-fair-lines
- [ ] Production Gate (typecheck + Next build) green on PR

## After ACCEPT

Ryan merges to `deploy-vercel` only. Rematerialize not required (display/contract only).
