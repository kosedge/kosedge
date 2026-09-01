# NBA Chapter 5 — PlayerProjection brief

**Phase:** One scorer. **No** props tags, **no** fantasy UI.  
**Depends on:** [#365](https://github.com/kosedge/kosedge/pull/365) merged  
**Stamp:** `nba-season-engine-v0.1`  
**Residual cap (identity):** `TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Ch1 shrink:** `TEAM_CARRY_SHRINK = 0.85` (**unchanged**)  
**Scorecard:** [`docs/NBA_CH5_PLAYER_PROJECTION_SCORECARD.md`](./NBA_CH5_PLAYER_PROJECTION_SCORECARD.md)

---

## What this PR does

One `PlayerProjection` per opening-night rotation slot (Ch2 minutes, not tonight’s injury list):

`MIN USG PTS REB AST STL BLK TOV 3PM PRA PR RA` + **σ each**.

Reads Ch2 talent × Ch2 minutes × team pace / implied_ppg from the rebased pack.  
`Σ PTS` identity-scaled to team `implied_ppg` within the Ch2 residual cap.

---

## Allowlist

| Item          | Path                                                    |
| ------------- | ------------------------------------------------------- |
| Schema + pack | `…/data/nba_player_projection_2026.json`                |
| Reader        | `player_projection.py`                                  |
| Builder       | `scripts/nba/build_player_projection_ch5.py`            |
| Tests         | `tests/test_nba_player_projection_ch5.py` (NBA-only CI) |
| Docs          | this brief + scorecard                                  |

---

## Forbidden (honored)

- Edge PLAY on props · fantasy board · new minute grid
- DARKO/EPM as the mean · team if · situation B2B (Ch3)
- CFB/NFL · hanging numbers on the live props stub

---

## Gates

- Every player with `MIN > 0` has the full vector + σ
- `Σ MIN = 240`, `Σ PTS` within residual cap
- σ is computed (season-rate dispersion × MIN), not a hardcoded 4
- CFB BALL@OSU still **−40.5**
- Zero prop tags in the UI / pack fields

---

## Done

Pack on disk. Props still dark.  
**Stop.** Chapter 6 is a desk on this object, not a second scorer. Chapter 3 situation can run in parallel after this pack exists — not instead of it.
