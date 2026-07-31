# NFL Pro Premium Readiness Report

**Date:** 2026-07-31 (P0 close-out pass)  
**Branches:** `cursor/nfl-pro-p0-preseason-camp-d62a` → `deploy-vercel`  
**Production:** https://www.kosedge.com  
**Prior run:** [NFL Pro premium population](https://cursor.com/agents/bc-eed62421-49a9-4f69-a47b-56976410a266) (~82/100)  
**Prior PR:** https://github.com/kosedge/kosedge/pull/25 (still open vs `nfl-second-order-edge`; tip already on `deploy-vercel`)

---

## 1. How close we are

**Score: 91 / 100 — subscription-ready for preseason week 1.**

**Verdict:** Core NFL Pro paths were already live at ~82. This pass closes the remaining P0 desk gaps: PRE boards no longer show empty model dashes (market + camp strength reference with honest labels), Training Camp Desk gives daily cadence, offseason standings/stats/injuries are explicitly labeled with auto-switch paths, and alias nav 404s (`/pro/nfl/odds`, `/intel`, `/hub`) redirect. Remaining points are true P1/P2: native PRE game sims, fresh 2026 injury weeks, writer-owned camp news breaks beyond the public beat feed, and external prediction-market venue joins.

---

## 2. What we have live now

| URL | Status | Quality | Data source |
| --- | --- | --- | --- |
| [/pro/nfl](https://www.kosedge.com/pro/nfl) → overview | **Live** | Hub + Camp Desk strip | Edge board + desk config |
| [/pro/nfl/camp](https://www.kosedge.com/pro/nfl/camp) | **Live (new)** | Beat map + ESPN camp headlines | `nfl-beat-writers.json` + ESPN news |
| [/pro/nfl/previews](https://www.kosedge.com/pro/nfl/previews) | **Live** | Premium index, 32/32 | `content/writers/season-previews-2026` |
| [/pro/nfl/previews/[TEAM]](https://www.kosedge.com/pro/nfl/previews/KC) | **Live** | Full articles + SEO | Writer markdown package |
| [/pro/nfl/slate/today](https://www.kosedge.com/pro/nfl/slate/today) | **Live** | PRE market+camp-ref + REG fair-lines | ESPN + Odds API PRE + sim expected-wins + Railway |
| [/pro/nfl/fair-lines](https://www.kosedge.com/pro/nfl/fair-lines) | **Live** | Strong | Model-service fair-lines (~168 REG) |
| [/odds/nfl](https://www.kosedge.com/odds/nfl) | **Live** | Strong | Odds API compare |
| [/pro/nfl/edges](https://www.kosedge.com/pro/nfl/edges) | **Live** | Strong (gated) | `/nfl/edges/today` |
| [/pro/nfl/props](https://www.kosedge.com/pro/nfl/props) | **Live** | Strong | Props board API |
| [/pro/nfl/execution](https://www.kosedge.com/pro/nfl/execution) | **Live** | Good | Fair-lines best-book table |
| [/pro/nfl/tracking](https://www.kosedge.com/pro/nfl/tracking) | **Live** | Good | `/nfl/clv-summary` |
| [/pro/prediction-market](https://www.kosedge.com/pro/prediction-market) | **Live** | Good futures desk | Preseason sim + preview markets |
| [/pro/nfl/projections](https://www.kosedge.com/pro/nfl/projections) | **Live** | Strong | Preseason sim bundle |
| [/pro/nfl/fantasy](https://www.kosedge.com/pro/nfl/fantasy) | **Live** | Good | Fantasy draft rankings API |
| [/pro/nfl/awards](https://www.kosedge.com/pro/nfl/awards) | **Live** | Good | Awards projections API |
| [/pro/nfl/teams](https://www.kosedge.com/pro/nfl/teams) | **Live** | Good | Team intel directory |
| [/pro/nfl/teams/[TEAM]](https://www.kosedge.com/pro/nfl/teams/KC) | **Live** | Preview wired | Season preview + intel tabs |
| [/pro/nfl/standings](https://www.kosedge.com/pro/nfl/standings) | **Live** | Labeled 2025 final | ESPN fallback → intel when ready |
| [/pro/nfl/stats](https://www.kosedge.com/pro/nfl/stats) | **Live** | Labeled sim strength | Bundle → intel when ready |
| [/pro/nfl/depth-charts](https://www.kosedge.com/pro/nfl/depth-charts) | **Live** | Strong | Intel depth-charts |
| [/pro/nfl/injuries](https://www.kosedge.com/pro/nfl/injuries) | **Live** | Labeled fallback week | Intel injuries + camp desk pointer |
| [/pro/power-ratings/nfl](https://www.kosedge.com/pro/power-ratings/nfl) | **Live** | Good | Expected-wins ranking |
| [/wall-chart/nfl-2026](https://www.kosedge.com/wall-chart/nfl-2026) | **Live** | Strong | Static 2026 schedule |
| [/edge-board/nfl](https://www.kosedge.com/edge-board/nfl) | **Live** | Strong | Fair-lines → board |
| [/pro/model-transparency](https://www.kosedge.com/pro/model-transparency) | **Live** | Good | Ops artifacts |
| [/pro/clv-tracker](https://www.kosedge.com/pro/clv-tracker) | **Live** | Good | CLV ops |

### Inventory actions completed this pass

1. PRE slate enrichment: ESPN/Odds API market + camp strength ref from REG expected-wins (honest labels; no fake PRE sims; PLAY tags still blocked).  
2. Training Camp Desk route + hub strip + footer/nav wiring.  
3. Standings/stats/injuries offseason fallbacks explicitly labeled with auto-switch copy.  
4. Alias redirects: `/pro/nfl/odds` → `/odds/nfl`, `/intel` → `/teams`, `/hub` → `/overview`.  
5. File-tracing includes for camp beat registry + slate/camp data paths.  

---

## 3. What we still need

### P0 before kickoff (preseason week 1 ~Aug 6–7)

- [x] **PRE fair numbers / context** — camp strength ref + market join on slate (not empty). Native PRE sims remain future work.  
- [x] **Odds API preseason events** — slate joins `americanfootball_nfl_preseason` when key authorizes; ESPN consensus remains fallback.  
- [x] **Editorial cadence** — Training Camp Desk live (beat map + public headlines); writer news-break templates remain in `docs/writers/TRAINING_CAMP_DESK.md`.  
- [x] **Smoke paywall UX** — Pro browse remains open under preview policy; stake tools stay desk-gated where product already gates.  

### P1 after kickoff / early REG

- [ ] Materialize **weekly standings + EPA stats** into `/nfl/intel/*` so pages stop using offseason fallbacks.  
- [ ] Matchup article briefs beyond generated edge-board cards (writer-owned weeklies).  
- [ ] Injuries feed freshness for 2026 camp / Week 1 (current intel may still land on 2025 W18).  
- [ ] Writer-owned camp **news breaks** published into the site (beyond curated beat links).  
- [ ] Execution monitor: book dispersion sparkline / line-move timing (beyond best-number table).  
- [ ] Native **PRE game sims** in model-service (Railway) when product wants true PRE fair-lines.

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
| **PRE model coverage** | Sims + fair-lines SQL remain REG-only (weeks 1–18) | Keep web camp-ref desk until Railway adds PRE schedule + optional PRE sim window; never attach season PLAY |
| **Data vendors** | PRE odds thin until books post; injuries may be aged | Odds API `americanfootball_nfl_preseason` joined in slate; ESPN fallback; evaluate SportRadar injuries if camp latency hurts |
| **Editorial cadence** | Public beat feed live; owned news breaks still manual | Publish Training Camp Desk hits via writer templates into `/pro/nfl/camp` or previews stream |
| **Paywall / billing** | Pro routes appear openly browsable under preview flags | Confirm Stripe/Clerk gate policy; don’t hide empty pages — gate stake actions |
| **Env hygiene** | Cloud agent `MODEL_SERVICE_URL` may differ from Railway prod | Production Vercel uses Railway `model-service-production-e253`; keep aligned |

---

## 5. Live URLs (start here)

- Hub: https://www.kosedge.com/pro/nfl  
- Camp Desk: https://www.kosedge.com/pro/nfl/camp  
- Articles index: https://www.kosedge.com/pro/nfl/previews  
- Example article: https://www.kosedge.com/pro/nfl/previews/KC  
- Weekly slate: https://www.kosedge.com/pro/nfl/slate/today  
- KEI Lines: https://www.kosedge.com/pro/nfl/fair-lines  
- Compare Odds: https://www.kosedge.com/odds/nfl  
- Edges: https://www.kosedge.com/pro/nfl/edges  
- Futures / prediction desk: https://www.kosedge.com/pro/prediction-market  

---

## 6. Score bridge (82 → 91)

| Item | Delta |
| --- | --- |
| PRE empty model dashes → market + camp-ref | +4 |
| Training Camp Desk + hub cadence | +3 |
| Labeled standings/stats/injuries fallbacks | +1 |
| Nav alias redirects / polish | +1 |
| Held back for native PRE sims + 2026 injuries + owned news breaks | −9 from 100 |

---

## Phase 0 checklist (living)

| Page | Before | After | Action taken |
| --- | --- | --- | --- |
| Season previews | Content only, no routes | Live 32/32 | Added `/pro/nfl/previews` |
| Weekly slate | 500 / stub → ESPN-only PRE | Live PRE market+camp-ref + REG | Slate enrichment |
| Camp Desk | Missing | Live beat+news | `/pro/nfl/camp` |
| Execution | 500 (sync params) | Live best-book table | Async + fair-lines |
| Tracking | 500 | Live CLV cards | `/nfl/clv-summary` |
| Standings | Empty intel | Labeled ESPN 2025 final | Fallback page |
| Stats | Empty intel | Labeled sim strength | Preseason bundle |
| Prediction market | Coming soon | Futures table | Sim + desk markets |
| Power ratings NFL | Empty JSON | Expected-wins ranks | Bundle fallback |
| Team preview slot | Coming soon | Live excerpt + link | Wired markdown |
| Team URL offseason | Remapped to BUF | Honors directory | `resolveTeamCode` fix |
| `/pro/nfl/odds` | 404 | Redirect to `/odds/nfl` | next.config redirect |
