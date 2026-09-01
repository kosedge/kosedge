# WNBA Chapter 7 — fantasy brief

**Phase:** Season board + slate from `PlayerProjection`. **No** props tags. **No** new scorer.  
**Stamp frozen:** `v0.1` · Ch2–Ch6  
**Scorecard:** [`docs/WNBA_CH7_FANTASY_SCORECARD.md`](./WNBA_CH7_FANTASY_SCORECARD.md)

---

## Formula

```text
fantasy_pts = f(PTS, REB, AST, STL, BLK, TOV, 3PM)   // one published scoring map
cats        = the same vector, unweighted
```

Same map as NBA Ch7 / NFL `fantasy_points_from_projection`.  
Do **not** invent a second set of means.

### Published scoring map (`kos_default_points`)

| Stat | Weight |
| ---- | -----: |
| PTS  |    1.0 |
| REB  |    1.2 |
| AST  |    1.5 |
| STL  |    3.0 |
| BLK  |    3.0 |
| TOV  |   −1.0 |
| 3PM  |    0.5 |

Season total = `fantasy_pts × 40` (per-game × WNBA RS length).

---

## Allowlist

- `/pro/wnba/fantasy` season ranks from Ch5 minutes
- Slate view: same players, same means, sorted by `fantasy_pts`
- `/wnba/fantasy/board?view=season|slate`
- Docs + 8-row scorecard
- WNBA-only CI

---

## Forbidden (honored)

New box stats · minute-grid rewrite · props PLAY · DFS optimizer · team if · retune Ch3/Ch4 · NBA/CFB/NFL

---

## Gates

- Every fantasy row’s box stats == Ch5 fields
- Σ MIN = 200 · team Σ PTS inside residual cap
- Props stub still untagged
- NBA fantasy unchanged · CFB BALL@OSU **−40.5**

---

## Done

Stop. Chapter 9 grades (schema + empty store) before playoffs Sep 27. **Not** a tag PR. **Not** 15 team previews this week.
