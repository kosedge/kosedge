# Fantasy draft board — model rank + hard reach cap

**Date:** 2026-08-22  
**Priority:** P0 — simple product rule

## One-sentence rule

**Sort by our rank. Cap how far above ADP we’ll put someone — hard stop ~1 round (12 picks), never 4 rounds.**

## Formula

1. Start at **model rank** (season projection points order — same spine as props/fantasy).
2. If `ADP − modelRank > 12` → board key = `ADP − 12` (cannot appear more than 12 picks before ADP).
3. If market ADP is ahead of model → mild bump up (`−0.35` slots per pick, cap 18).
4. Sort by board key → assign **draft rank** 1…N.

Unmatched ADP → model rank only. No invented blend.

Code: `apps/web/lib/fantasy/desk-rank-policy.ts` · applied in `load-desk.ts`.

Methods line: *Rank = our projections; hard cap ~1 round above ADP. Default PPR.*

## Five before/after examples

| Player | Model | ADP | Gap | Board key | Draft story |
|--------|-------|-----|-----|-----------|-------------|
| WR reach | 24 | 72 | 48 (4 rds) | **60** | Not #24 — `Wait` |
| QB reach | 3 | 28 | 25 | **16** | Not #3 — capped |
| Henry RB | 30 | 40 | 10 | **30** | Small `Reach`, stays |
| Gibbs RB | 17 | 1 | −16 | **~11** | `Value` bump |
| CMC | 1 | 3 | 2 | **1** | `Fair` at top |

## Smell tests

| # | Check | Pass |
|---|--------|------|
| 1 | No ~4-round reach on default board | ✅ `assertNoHardReachViolations` |
| 2 | First load draft rank 1…N | ✅ default tab `draft` |
| 3 | ADP secondary; badges ≤3 words | ✅ Tag column |
| 4 | PPR default | ✅ |
| 5 | K/DST unchanged | ✅ |

## UI stripped

- No CHECK ROLE chips on draft desk rows
- No Fantasy Expert essay block on main desk
- Badges: Fair / Reach / Value / Wait only

## Non-goals

New engine, resim, Edge, mock rewrite, role-check system on desk.
