# CFB Subscription-Ready Research Desk — product lock

**Date:** 2026-08-15  
**Branch:** `feat/cfb-subscription-ready-lock` → `deploy-vercel` (stacked on #241–#243)  
**Doctrine:** Model = research fair. `used_in_spread=false`. No KEI. No PLAY/LEAN. No CFP%.  
**Not a release gate for Edge.** Subscription value today is power + matchup fairs + season projections + honesty.

---

## What Pro gets today

| Surface | What the user gets |
| --- | --- |
| `/pro/cfb/model` | Research contract, engine/power/N/as_of, fidelity, power ladder |
| `/pro/cfb/project-game` | Research-fair spread, total, WP, σ, drivers |
| `/pro/cfb/slate` | Official W0/W1 ESPN board → deep-link auto-run |
| `/pro/cfb/projections` | Frozen-SoT **N=10,000** E[wins] + p10–p90. CFP/natty omitted |
| `/pro/cfb/teams` | 136-row Power SoT, fill labels, next-game → project-game (mobile cards) |
| `/edge-board/cfb` | **Markets only** — KEI / Edge / Tag blank |

Power: `cfb-power-sot-v0.15-20260814` · as_of **2026-08-14** · n=136  
Projections: `cfb-season-projections-v0.15-n10000-20260814` · **N=10,000** · as_of **2026-08-14**

Overview path: **Model → Project Game → Slate**. Dead KEI / Fair Lines / Edges / Tempo / Props / generic Power Ratings CTAs redirect to the research desk. Single Power SoT lives on `/pro/cfb/teams`.

---

## What is intentionally not sold (Edge)

- No CFB KEI line, PLAY/LEAN, or Edge Tag
- `used_in_spread` stays false
- No CFP / natty percentages
- No open-line blend (55 opens exist; diagnostic is cold / short-favorite; closes=0)
- Hist + live bias lives in ops (`cfb-market-diagnostic-20260814.md`, `cfb-live-open-diagnostic-20260815.md`) — not scare copy on the desk

---

## Re-pull + re-diagnostic (Week 3+)

```bash
python scripts/cfb/cfb pull-opens --weeks 0-3
python scripts/cfb/cfb live-open
python scripts/cfb/cfb diagnostic 2026
```

Do **not** write a KEI design brief until:

1. `n_closes` > 0 on a usable W0–2+ slice  
2. Mid-range \|line\| buckets are no longer thin  
3. Held-out plan exists (not this file)  
4. Live vs-open still does not get papered over  

Until then: research desk only.

---

## Smoke table

**Production HTTP 2026-08-15:** all primary CFB Pro routes returned **200** (auth wall may wrap the HTML). Slate + projections are no longer 404. Leftover KEI/Fair Lines **shells** still 200 until this PR merges (then they redirect).

| Route | Prod HTTP | After this stack |
| --- | --- | --- |
| `/pro/cfb/model` | 200 | 200 · research contract, no `used_in_spread` jargon |
| `/pro/cfb/project-game` | 200 | 200 |
| `/pro/cfb/slate` | 200 | 200 · official W0/W1 |
| `/pro/cfb/projections` | 200 | 200 · N=10,000 artifact |
| `/pro/cfb/teams` | 200 | 200 · 136 + mobile cards |
| `/pro/cfb/overview` | 200 | 200 · Model → Project Game → Slate |
| `/edge-board/cfb` | 200 | 200 · markets only |
| `/pro/cfb/fair-lines` | 200 (old shell) | **redirect → project-game** |
| `/pro/cfb/edges` | 200 (old shell) | **redirect → model** |
| `/pro/kei-lines/cfb` | 200 (empty KEI) | **redirect → model** |
| `/pro/cfb/tempo` | 200 | **redirect → project-game** |
| `/pro/cfb/props` | 200 | **redirect → project-game** |
| `/pro/power-ratings/cfb` | 200 | **redirect → teams (SoT)** |
| `/pro/cfb/slate/today` | 200 | **redirect → /pro/cfb/slate** |

**P0 remaining:** merge this stack onto `deploy-vercel` so dead KEI/Fair Lines CTAs stop rendering. No invented lines.

---

## Confirm

Still **no CFB Edge**. Lines stay earned.
