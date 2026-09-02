# NHL Chapter 7 — fantasy brief

**Phase:** Season board + slate from `PlayerProjection`. **No** props tags. **No** new scorer.  
**Stamp frozen:** `v0.1` · Ch2–Ch6  
**Scorecard:** [`docs/NHL_CH7_FANTASY_SCORECARD.md`](./NHL_CH7_FANTASY_SCORECARD.md)

---

## Formula

```text
fantasy_pts = f(G, A, SOG[, SAVES])   // one published scoring map
cats        = the same vector, unweighted
```

Skater rows from Ch5 skater vector. Goalie rows from Ch5 goalie vector — map includes **SAVES** (no `W` in Ch5 → no invented wins). Goalies are never double-counted as skaters.

NFL/NBA analog: `fantasy_points_from_projection`. Do **not** invent a second set of means.

### Published scoring map (`kos_default_points`)

| Stat  | Weight | Applies to |
| ----- | -----: | ---------- |
| G     |    3.0 | skater     |
| A     |    2.0 | skater     |
| SOG   |    0.4 | skater     |
| SAVES |    0.2 | goalie     |

`P` is display-only (G+A) — never weighted.  
Season total = `fantasy_pts × 82` (opening-night per-game × season length).

---

## Allowlist

- `/pro/nhl/fantasy` season ranks from Ch5
- Slate view: same means
- `/nhl/fantasy/board?view=season|slate`
- Docs + 10-row scorecard
- NHL-only CI

---

## Forbidden

New G/A/SOG · new TOI · props PLAY · DFS optimizer · team if · retune Ch3/Ch4 · NBA/WNBA/CFB/NFL

---

## Gates

- Box stats == Ch5 fields
- Goalie `start_share` still ~1.0 per team
- Props stub still untagged (Ch6 dark)
- KEINHL from Ch4 unchanged (FLA@CAR puck −0.94)
- Other sports untouched

---

## Done

Stop. Chapter 9 grades before opening night Sep 29. **Not** a tag PR. **Not** 32 previews until camps (~Sep 16).
