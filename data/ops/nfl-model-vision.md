# KosEdge NFL model vision

North-star alignment note for humans and agents. Product bar, locked contracts, and sprint framing — not an implementation spec.

## What this is for

KosEdge NFL is not a toy ranking page. It is a professional NFL handicapping and projection system: for personal use now, and for an eventual premium product later. Every modeling and ops decision should be judged against that bar.

## What the model must serve at once

The same core must support these surfaces together — not as separate toys:

1. **Betting lines** — Fair spreads, totals, and moneylines. KEI is the final handicap. Edge is KEI versus market only.
2. **Full season engine** — Hierarchical simulation: team strength → game script → player usage → player production / box scores.
3. **Real use cases** — Sides and totals on regular-season games; survivor pathing; fantasy and guillotine; future game projection (e.g. “Week 7 IND vs MIN — what does the box look like?”); finite season distributions of wins, yards, and TDs.
4. **Locked contract** — Model = pure research fair snapshot. KEI = model plus late information / reprice. Edge / Tag = KEI vs market. Never raw model vs market for PLAY.
5. **Operating standard** — In-house as much as possible. No demo bumps in real mode. No preseason handicapping. Reprice on real information (injuries, inactives, weather, rest/travel, QB confirmation). Proof via logged lines, closes, results, and CLV.
6. **Bar** — Top-tier professional. Smell tests must pass. If the hierarchy is wrong, the model is wrong. Lines must be the best we can make with an owned process and limited paid data.

## Sprint framing

| Sprint | Scope | Status |
|--------|--------|--------|
| **Sprint 1** | Fix the broken demo-strength path that contaminated “real” packaged / launch-research hierarchies | Done |
| **Sprint 2** | Football-native efficiency backbone that drives everything above — upstream strength-core replacement, **not** a greenfield season-engine rewrite | Done (v1): `nfl-efficiency-backbone-v1-20260807.md` · **v1.1** ST + true EPA splits: `nfl-efficiency-backbone-v1.1-20260808.md` · wired: `nfl-strength-wired-through-engine-20260808.md` |

## What stays vs what changes (Sprint 2)

**Stays**

- Hierarchical engine structure
- Injury shocks
- Depth / usage
- Game script / red-zone / coaching hooks
- Season sim + survivor + game boxes
- Model vs KEI contract
- Edge Board path
- Fantasy desk

**Changes**

- Source of team strength → in-house NFL efficiency backbone wired into the existing strength slot

## Related docs

- [Sprint 1 after-action](nfl-team-strength-fix-after-action-20260807.md) — demo-strength contamination fix
- [Packaged EPA priors fix](nfl-packaged-epa-priors-fix-20260807.md) — related Sprint 1 packaging / priors work
- [Sprint 2 efficiency backbone v1](nfl-efficiency-backbone-v1-20260807.md) — definitions, materialize path, hierarchy sample
