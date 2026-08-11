# Fantasy Mock CPU Guards + Builder K/DST Honesty (2026-08-11)

## Status

**Shipped** on `deploy-vercel` via [#172](https://github.com/kosedge/kosedge/pull/172) (`6811d246`, merged 2026-08-10). Re-verified green on tip `af602302` (includes #183) on 2026-08-11.

## CPU hard guards (`apps/web/lib/fantasy/mock-cpu.ts`)

Round-based max ADP reach (`maxAdpDeviationForRound`):

| Round | Max ADP ahead of overall pick (12-team) |
|-------|----------------------------------------|
| R1 | `max(12, floor(n×1.25))` ≈ 15 |
| R2 | `floor(n×2.5)` ≈ 30 |
| R3–4 | `floor(n×4)` ≈ 48 |
| R5–8 | `floor(n×6)` ≈ 72 |
| R9+ | `floor(n×10)` ≈ 120 |

Additional R1 absolute blocks:

- Nothing with ADP past end of R2 (`> teamCount×2`)
- TE with ADP `> teamCount×1.75`
- QB with ADP `> teamCount×2.5`

Early rounds damp pure ADP-value (`valueDelta` ×0.15 in R1–2 / ×0.4 in R3–4) and lean on VORP + need + rank. Existing R1 QB bias dampening + late QB2 suppress unchanged. Hard-blocked candidates score `-Infinity` and are filtered from the scoring pool.

## Builder grade (`apps/web/lib/fantasy/team-builder.ts`)

When `board` is passed and has no K/DST rows (preseason skill board):

- `rosterNeeds` sets want K/DST = 0
- `teamGrade` does not list K/DST as holes
- Desk copy (“K/DST unavailable… do not ding grades”) matches scoring

Does **not** invent kicker rankings.

## Tests (2026-08-11 re-run)

```text
mock-cpu.test.ts       5 passed
team-builder.test.ts   5 passed
mock-r1-cpu.test.ts    4 passed  (incl. ADP-269 TE never in top-5 / 1.03 stress)
```

## Banked product note (not in this change)

5k Game Box default bump remains **deferred**. Cache strategy (see `nfl-sim-depth-precision-20260811.md`):

- key ≈ `run_id + game_id + roster_snapshot_id + scenario hash + engine_version + n`
- Edge Board list never inlines 16×5k
- Week 1 prewarm after publish
- Interactive default stays **2k** + cache until warm 5k is operationally ready
