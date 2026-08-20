# Playing-time diagnose — 2026-08-20 (Phase 0)

**LIVE stays true.** Top-20 fantasy board is not ghost-heavy.

Prod snapshot: `GET /nfl/fantasy/draft-rankings?season=2026&scoring_profile=half_ppr` (SUM cap 17, remat 2026-08-20). Weekly: `/nfl/fantasy/rankings?season=2026&week=1`. Depth SoT: packaged `nfl_depth_chart_2026_w1.json`. Expert: www `/pro/nfl/fantasy` Fantasy Expert strip.

Companion: `data/ops/nfl-spine-phase0-opportunity-20260820.md`.

---

## LIVE gate (top 20)

| # | Player | Shape |
|---|--------|-------|
| 1 | C.McCaffrey SF RB | 17g · 1304 rush · 688 rec · 342 pts |
| 2 | B.Robinson ATL RB | 1552 rush |
| 3 | T.Lawrence JAX QB | 3669 pass |
| 8 | J.Chase CIN WR | 1791 rec |
| 12–13 | Prescott / Burrow | 4213 / **4297** pass |

QB1/RB1/WR1 volume looks like starters. **Keep LIVE. Do not stop before Phase 1.**

---

## Sample

| Player | Depth SoT | Season SUM | Implied share | Rank / VOR | Expert rail | Class |
|--------|-----------|------------|---------------|------------|-------------|-------|
| **A.O'Connell** LV | **QB3** `depth_order=3` | **3065** pass · 17g | **~93%** of LV pass yards | #54 / QB30 · VOR −73 · ADP **438** cross_format | Card #54; not top-3 strip (`valueDelta` null) | **A usage** |
| K.Cousins LV | **QB1** starter | 183 pass | ~6% | #832 / QB39 | starved | A (inverse) |
| F.Mendoza LV | **QB2** backup | **absent** from 940-row board | — | HALF ADP ~168 | missing | grain/id miss |
| **B.Cook** NYJ | **QB3** | **3302** pass | room primary vs Geno | #46 / QB27 | **Yes** — Expert #1 vs ADP ~297 | **A usage** |
| G.Smith NYJ | **QB1** | 215 pass | residual | #786 | starved | A (inverse) |
| **Q.Ewers** MIA | QB2/3 class | 3226 pass | starter-class | #50 / QB29 | not top-3 | **A usage** |
| **P.Dorsett** LV WR | depth dust | 478 rec | WR4-class targets | #167 / WR56 | no (ADP too deep / not in strip) | **A** (grain + WR4 prior) |
| **L.Treadwell** IND WR | depth dust | 555 rec | WR4-class | #152 / WR48 | no | **A** (grain) |
| **J.Burrow** CIN | QB1 | **4297** pass | team primary | #13 / QB7 | no (not a “value” gap) | **control** |
| **J.Allen** BUF | QB1 | 3533 pass + 361 rush | team primary | #6 / QB2 | no | **control** |

Weekly w1: O’Connell **11.75** half-PPR vs Cousins **0.46**; Cook **13.05** vs Geno **0.60**.

Expert strip on www (pre-gate): B.Cook, B.Smith (KC 1089 rush, ADP ~319), S.Sanders. Amplifies largest ADP gaps. Does not invent O’Connell’s 3065 yards.

---

## Mechanism

`compute_qb_starter_shares` ranked on **team-scoped prior attempts**. Same-team last-year passer (O’Connell, Cook) beat this year’s signed QB1 (Cousins, Geno) who have **0** team-scoped attempts. Winner-take-most **0.92 / 0.06 / 0.02**.

---

## Classification summary

- Ghost QBs: **A — real volume in spine (usage)**
- WR4 dust: **A** (roster-width intercepts + WR4 prior 0.06), not ~0 vs ADP
- Filter/expert: **amplifies A**, would be B only if volume were ~0 (it is not)
- Top board: **sane** → Phase 1 ship is in bounds
