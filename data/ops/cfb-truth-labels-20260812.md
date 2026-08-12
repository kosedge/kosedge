# CFB truth labels — 2026-08-12

Date: 2026-08-12  
Branch: `feat/cfb-truth-labels` → `deploy-vercel`  
Depends on: CFB truth audit (#210) findings  
Doctrine: Same as NFL. MODEL desks labeled. No KEI invention. Honest empty > fake edge.

## One-liner (append under `data/ops/cfb-truth-audit-20260812.md`)

**Labels shipped:** `/pro/cfb/model` and `/pro/cfb/project-game` show **PRESEASON + MODEL** (MODEL only after Week 0 / 2026-08-29). Edge Board CFB stays **LIVE books / no KEI** — Project Game is not copied on as edge.

## Surfaces

| Surface | Badge | Copy |
|---------|--------|------|
| `/pro/cfb/model` | PRESEASON + MODEL | not a published handicap |
| `/pro/cfb/project-game` (hub + result card) | PRESEASON + MODEL | MODEL research; books ≠ KEI |
| `/edge-board/cfb` | LIVE | live sportsbook Open/Best; KEI columns blank |

Shared `TruthStateBadge` (NFL wrapper keeps `nfl-truth-state` test id). Cutoff: `CFB_PRESEASON_CUTOFF_ISO[2026] = 2026-08-28`.

## Not in this PR

KEI, densified-schedule rewrite, roster refresh, joining board to project-game.
