# NFL Pro Premium Readiness Report

**Date:** 2026-07-31  
**Branches:** `cursor/nfl-pro-premium-populate-a266` (PR #25), shipped to `deploy-vercel`  
**Production:** https://www.kosedge.com  
**PR:** https://github.com/kosedge/kosedge/pull/25

---

## 1. How close we are

**Score: 82 / 100 — subscription-ready for preseason week 1 desk use, with known enterprise gaps.**

**Verdict:** A paying user can now click through the entire NFL Pro hub without hitting empty shells, 500s, or “coming soon” dead-ends on core paths. The 32 season previews are public. The weekly slate shows real preseason schedule + regular-season fair-lines/odds/publish tags. Betting desk surfaces (KEI, edges, props, compare odds) were already live and remain the strongest product. Remaining gaps are mainly in-season intel tables (standings/stats EPA feeds empty until weeks play), PRE-game model fair-lines (sims are REG-only today), and dedicated prediction-market venue feeds.

---

## 2. What we have live now

| URL | Status | Quality | Data source |
| --- | --- | --- | --- |
| [/pro/nfl](https://www.kosedge.com/pro/nfl) / overview | **Live** | Strong hub IA + matchup scroller | Edge board + desk config |
| [/pro/nfl/previews](https://www.kosedge.com/pro/nfl/previews) | **Live** | Premium index, 32/32 | `content/writers/season-previews-2026` |
| [/pro/nfl/previews/[TEAM]](https://www.kosedge.com/pro/nfl/previews/KC) | **Live** | Full articles + SEO | Writer markdown package |
| [/pro/nfl/slate/today](https://www.kosedge.com/pro/nfl/slate/today) | **Live** | Preseason + REG weeks | ESPN schedule + Railway fair-lines |
| [/pro/nfl/fair-lines](https://www.kosedge.com/pro/nfl/fair-lines) | **Live** | Strong | Model-service fair-lines (~168) |
| [/pro/nfl/edges](https://www.kosedge.com/pro/nfl/edges) | **Live** | Strong (gated) | `/nfl/edges/today` |
| [/odds/nfl](https://www.kosedge.com/odds/nfl) | **Live** | Strong (272 rows) | Odds API compare |
| [/pro/nfl/props](https://www.kosedge.com/pro/nfl/props) | **Live** | Strong | Props board API |
| [/pro/nfl/execution](https://www.kosedge.com/pro/nfl/execution) | **Live** | Good (was 500) | Fair-lines best-book table |
| [/pro/nfl/tracking](https://www.kosedge.com/pro/nfl/tracking) | **Live** | Good (was 500) | `/nfl/clv-summary` |
| [/pro/prediction-market](https://www.kosedge.com/pro/prediction-market) | **Live** | Good futures desk | Preseason sim + preview markets |
| [/pro/nfl/projections](https://www.kosedge.com/pro/nfl/projections) | **Live** | Strong | Preseason sim bundle |
| [/pro/nfl/fantasy](https://www.kosedge.com/pro/nfl/fantasy) | **Live** | Good | Fantasy draft rankings API |
| [/pro/nfl/awards](https://www.kosedge.com/pro/nfl/awards) | **Live** | Good | Awards projections API |
| [/pro/nfl/teams](https://www.kosedge.com/pro/nfl/teams) | **Live** | Good | Team intel directory |
| [/pro/nfl/teams/[TEAM]](https://www.kosedge.com/pro/nfl/teams/KC) | **Live** | Preview wired (URL remap fixed) | Season preview + intel tabs |
| [/pro/nfl/standings](https://www.kosedge.com/pro/nfl/standings) | **Live** | Prior-season final | ESPN 2025 fallback (intel empty) |
| [/pro/nfl/stats](https://www.kosedge.com/pro/nfl/stats) | **Live** | Offseason strength table | Preseason sim expected wins |
| [/pro/nfl/depth-charts](https://www.kosedge.com/pro/nfl/depth-charts) | **Live** | Strong | Intel depth-charts |
| [/pro/nfl/injuries](https://www.kosedge.com/pro/nfl/injuries) | **Live** | Strong (prior season rows) | Intel injuries |
| [/pro/power-ratings/nfl](https://www.kosedge.com/pro/power-ratings/nfl) | **Live** | Good | Expected-wins ranking |
| [/wall-chart/nfl-2026](https://www.kosedge.com/wall-chart/nfl-2026) | **Live** | Strong | Static 2026 schedule |
| [/edge-board/nfl](https://www.kosedge.com/edge-board/nfl) | **Live** | Strong | Fair-lines → board |
| [/pro/model-transparency](https://www.kosedge.com/pro/model-transparency) | **Live** | Good | Ops artifacts |
| [/pro/clv-tracker](https://www.kosedge.com/pro/clv-tracker) | **Live** | Good | CLV ops |

### Inventory actions completed this run

1. Created public season-preview routes (index + 32 articles).  
2. Replaced stub/500 slate with real PRE + REG board.  
3. Fixed async `params` crashes on execution/tracking/slate.  
4. Populated standings/stats/prediction-market/power-ratings with best available data.  
5. Wired Team Preview slots to real articles; expanded writer matrix to 8 owners.  
6. Fixed offseason team URL remap bug (`/teams/KC` → BUF when intel empty).  
7. Shipped to `deploy-vercel` (prod).  

---

## 3. What we still need

### P0 before kickoff (preseason week 1 ~Aug 6–7)

- [ ] **PRE fair-lines / sims** — model-service currently returns REG only; slate PRE cards use ESPN consensus until PRE sims exist.  
- [ ] **Odds API preseason events** — compare board is REG-heavy (Sept+); confirm PRE markets appear as books post them.  
- [ ] **Editorial cadence** — camp news-breaks per `docs/writers/TRAINING_CAMP_DESK.md` (practice reports, cuts, QB competitions) linked from hub.  
- [ ] **Smoke paywall UX** — confirm intentional auth walls vs open Pro browse; users should see structure even if stake tools gate.

### P1 after kickoff / early REG

- [ ] Materialize **weekly standings + EPA stats** into `/nfl/intel/*` so pages stop using offseason fallbacks.  
- [ ] Matchup article briefs beyond generated edge-board cards (writer-owned weeklies).  
- [ ] Injuries feed freshness for 2026 camp / Week 1 (current intel defaults to 2025 W18).  
- [ ] Execution monitor: book dispersion sparkline / line-move timing (beyond best-number table).

### P2 nice-to-have

- [ ] External prediction-market venue join (Kalshi/Polymarket-class), not just model futures.  
- [ ] Dedicated player preview index (hub currently routes “Player Previews” → awards).  
- [ ] SportRadar / OddsBlaze if Odds API depth or injury latency becomes insufficient.  
- [ ] Mobile polish pass on slate + preview typography.  
- [ ] Power ratings JSON export (`power_ratings_nfl.json`) instead of sim-derived expected wins only.

---

## 4. Enterprise gaps

| Area | Gap | Recommended path |
| --- | --- | --- |
| **Data vendors** | PRE odds thin; injuries aged to 2025 | Keep Odds API; add PRE season_type to fair-lines job; evaluate SportRadar injuries if camp latency hurts |
| **Editorial cadence** | Season previews shipped; camp notebook not on web yet | Publish Training Camp Desk hits to `/pro/nfl/previews` or a `/pro/nfl/camp` stream |
| **Model coverage** | 168 REG fair-lines through ~W12; 0 PRE | Schedule PRE sim window before HOF game; keep publish tags blocking PRE PLAY |
| **Paywall / billing** | Pro routes appear openly browsable | Confirm Stripe/Clerk gate policy; don’t hide empty pages — gate stake actions |
| **Mobile polish** | Hub dense but usable | Compact slate cards + preview reading measure on small screens |
| **Env hygiene** | Cloud agent `MODEL_SERVICE_URL` pointed at slim non-NFL service | Production Vercel uses Railway `model-service-production-e253`; keep aligned |

---

## 5. Live URLs (start here)

- Hub: https://www.kosedge.com/pro/nfl  
- Articles index: https://www.kosedge.com/pro/nfl/previews  
- Example article: https://www.kosedge.com/pro/nfl/previews/KC  
- Weekly slate: https://www.kosedge.com/pro/nfl/slate/today  
- KEI Lines: https://www.kosedge.com/pro/nfl/fair-lines  
- Compare Odds: https://www.kosedge.com/odds/nfl  
- Edges: https://www.kosedge.com/pro/nfl/edges  
- Futures / prediction desk: https://www.kosedge.com/pro/prediction-market  

---

## Phase 0 checklist (living)

| Page | Before | After | Action taken |
| --- | --- | --- | --- |
| Season previews | Content only, no routes | Live 32/32 | Added `/pro/nfl/previews` |
| Weekly slate | 500 / stub template | Live PRE+REG | New NFL slate builder |
| Execution | 500 (sync params) | Live best-book table | Async + fair-lines |
| Tracking | 500 | Live CLV cards | `/nfl/clv-summary` |
| Standings | Empty intel | ESPN 2025 final | Fallback page |
| Stats | Empty intel | Sim strength table | Preseason bundle |
| Prediction market | Coming soon | Futures table | Sim + desk markets |
| Power ratings NFL | Empty JSON | Expected-wins ranks | Bundle fallback |
| Team preview slot | Coming soon | Live excerpt + link | Wired markdown |
| Team URL offseason | Remapped to BUF | Honors directory | `resolveTeamCode` fix |
