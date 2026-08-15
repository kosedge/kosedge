# CFB Full Product Closeout — Research Desk

**Date:** 2026-08-14  
**Branch:** `feat/cfb-full-product-closeout` → `deploy-vercel` (stacked on #233–#239)  
**Engine:** `cfb-season-engine-v0.14-efficiency-backbone`  
**Doctrine:** Model = research fair only. `used_in_spread` stays **false**. No KEI. No Edge Tag. No PLAY/LEAN. No invented CFP%.

This phase closes the **research desk**, not betting Edge.

---

## Done checklist

| Surface | Route | Status |
| --- | --- | --- |
| Model hub | `/pro/cfb/model` | Version, as_of, slate_complete, 889-game coverage, research contract, desk links |
| Project Game | `/pro/cfb/project-game` | Spread / total / WP / team totals / σ / drivers. Week 0 accepted. Deep-link from slate |
| Official slate | `/pro/cfb/slate` | Week 0 / Week 1 from official ESPN pack (not Odds “tonight”) |
| Season projections | `/pro/cfb/projections` | Research E[wins] + p10–p90 on official slate. CFP/natty omitted. Banner honest |
| Team DNA | `/pro/cfb/teams` | 136/136 official rows. Warehouse fills labeled. Next-opponent → project-game |
| Edge Board | `/edge-board/cfb` | Markets only. Blank KEI. LIVE books ≠ KEI |
| Nav | CFB Pro header | Overview · Model · Project Game · Slate · Projections · Teams · Edge Board |
| API | `POST /cfb/season-engine/project-game` | `week` ge=0; FCS codes up to 48 chars |
| Status desk | `GET /cfb/season-engine/status` | `desk.week_board` + `desk.team_dna` |

Honesty pass:

- No “Coming soon” on shipped CFB desks
- No false degraded banner when the engine is healthy
- `/pro/cfb/slate/today` redirects to the official week board
- Tempo CFB CTA no longer says “KEI Lines”
- Standings / Havoc Stats 404s removed from CFB nav

---

## Engine / slate facts (unchanged this PR)

- Engine version: **v0.14-efficiency-backbone**
- Calibration: v0.13 tanh (`SCALE=0.80`, `TAU=26`)
- Official slate: ESPN 2026, **889** games, `slate_complete=true`
- Roster: **136/136** official FBS
- Market diagnostic (#239): hist W0–1 **47.7% ATS / MAE 8.36**, cold / short-favorite
- 2026 Week 0–2 market n=0 (lake is Nov futures snaps only)

---

## What waits (not this phase)

1. **2026 opens exist** — books post Week 0–2 numbers we can join
2. **Market diagnostic join** — model vs open/close on live 2026, not hist reconstruction
3. **Possible KEI design post–Week 3** — only if a held-out diagnostic earns it
4. `used_in_spread = true` — forbidden until (3)
5. CFB Edge Tag / PLAY / LEAN
6. CFP% / natty as product truth (ESPN postseason empty; stay stub)
7. In-season efficiency updates as a live product path

Betting Edge on CFB remains **off**.

---

## Smoke table

Local (after `pnpm run:3000` + model-service):

| # | Check | Expected |
| --- | --- | --- |
| 1 | `/pro/cfb/model` | 200 · version contains `v0.14` · slate_complete · used_in_spread=false |
| 2 | `/pro/cfb/project-game?home=TCU&away=UNC&week=0&neutral=1` | spread / total / σ |
| 3 | `/pro/cfb/slate` and `?week=1` | official Week 0 / Week 1 rows |
| 4 | `/pro/cfb/projections` | research banner · E[wins] table · CFP omitted |
| 5 | `/pro/cfb/teams` | 136 DNA rows |
| 6 | `/edge-board/cfb` | markets-only · no fake KEI |
| 7 | `GET /cfb/season-engine/status` | `used_in_spread: false` |
| 8 | Mobile nav | Model · Project Game · Slate · Projections · Teams usable |

Production / preview URLs: fill after Vercel preview on this PR.

| # | Preview / prod |
| --- | --- |
| 1 | `/pro/cfb/model` |
| 2 | `/pro/cfb/project-game?home=TCU&away=UNC&week=0&neutral=1` |
| 3 | `/pro/cfb/slate` |
| 4 | `/pro/cfb/projections` |
| 5 | `/pro/cfb/teams` |
| 6 | `/edge-board/cfb` |

---

## Explicit non-goals (held)

- used_in_spread flip
- CFB KEI / Edge tags / PLAY
- Open-line blend
- Invented CFP probabilities
- New efficiency features
- NFL work
