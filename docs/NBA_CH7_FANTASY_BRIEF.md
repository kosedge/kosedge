# NBA Chapter 7 — fantasy brief

**Phase:** Season board + slate from `PlayerProjection`. **No** props tags. **No** new scorer.  
**Stamp frozen:** `v0.1` · Ch2–Ch6  
**Scorecard:** [`docs/NBA_CH7_FANTASY_SCORECARD.md`](./NBA_CH7_FANTASY_SCORECARD.md)

---

## Formula

```text
fantasy_pts = f(PTS, REB, AST, STL, BLK, TOV, 3PM)   // one published scoring map
cats        = the same vector, unweighted
```

NFL analog: `fantasy_points_from_projection` in `nfl_player_projection_engine.py`.  
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

Season total = `fantasy_pts × 82` (opening-night per-game × season length).

---

## Allowlist

- `/pro/nba/fantasy` season ranks from Ch5 opening-night minutes
- Slate view: same players, same means, sorted by `fantasy_pts`
- `/nba/fantasy/board?view=season|slate`
- Docs + 10-row scorecard
- NBA-only CI

---

## Forbidden (honored)

New PTS/REB/AST · minute-grid rewrite · props PLAY/LEAN · DFS lineup optimizer · team if · retune Ch3/Ch4 · CFB/NFL

---

## Gates

- Every fantasy row’s box stats == Ch5 fields
- Team Σ PTS still inside ±3.0
- Props stub still untagged
- CFB BALL@OSU **−40.5**

---

## Done

Stop. Next is Chapter 8 chrome (previews / camp) or Chapter 9 grades — **not** a tag PR.
