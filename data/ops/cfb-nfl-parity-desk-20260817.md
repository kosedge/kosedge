# CFB → NFL-parity research desk — 2026-08-17

Branch: `feat/cfb-nfl-parity-desk` → `deploy-vercel`  
Doctrine: Model = research fair only. `used_in_spread=false`. No KEI, no PLAY/LEAN, no Edge tags on CFB.

## Not for firing

This desk is **not a betting card**. Project Game numbers are research-fair. Edge Board CFB is live books only. Do not treat E[wins], power index, or preview “the number” as a wagering instruction.

## Week 3 KEI gate

KEI / `used_in_spread=true` / PLAY tags stay off until the Week 3 gate is explicitly earned. Do not invent lines to look done.

## Artifact

| Field | Value |
|-------|--------|
| Engine | `cfb-season-engine-v0.15-power-sot` |
| Power | `cfb-power-sot-v0.15-20260814` · 136 FBS |
| Projections | `cfb-season-projections-v0.15-n10000-20260814` |
| N | **10,000** |
| as_of | 2026-08-14 |
| used_in_spread | **false** |
| kei | false |
| CFP / natty | omitted |

Power top 5: OSU, ORE, MISS, MIA, IU — Power-4, not inverted G5-over-P4.  
E[wins] top can include USF / UNT / TOL / HAW / JMU because of schedule. The projections page banners that split.

Affiliation overlay: a few SoT rows still say Independent (MIZZ, UNT, TOL, …). Display filter remaps them; power index is unchanged.

## Team previews shipped (9)

OSU, ORE, MISS, MIA, ND, UTAH, USF, BOISE, JMU  
Format: Title · date · Bottom line · The number · Quick projection · Roster snapshot · What matters most · Schedule notes · Betting angles to track · What would change · Model note. KosEdge + date only.

## Conference previews shipped (7)

SEC · Big Ten · ACC · Big 12 · Independent / Notre Dame note · AAC · Mountain West

## Smoke table (prod)

| URL | Expect | Pass |
|-----|--------|------|
| `/pro/cfb/overview` | Start-here 1–5 | |
| `/pro/cfb/slate` | W0 + W1, project-game links | |
| `/pro/cfb/project-game` | Research fair, no hang | |
| `/pro/cfb/projections` | N=10000, used_in_spread=false | |
| `/pro/cfb/teams` | 136 rows + conference filter | |
| `/pro/cfb/teams/osu` | Power + DNA + next game | |
| `/pro/cfb/previews` | ≥8 team previews | |
| `/pro/cfb/previews/osu` | House format | |
| `/pro/cfb/conferences` | P4 + ND + 2 G5 | |
| `/pro/cfb/conferences/sec` | SEC preview | |
| `/edge-board/cfb` | Markets only, no KEI | |
| `/pro/power-ratings/cfb` | Redirect → `/pro/cfb/teams` | |
| `/pro/cfb/slate/today` | Redirect → `/pro/cfb/slate` | |

Fill Pass after Production Smoke + manual click-through.
