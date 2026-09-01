# WNBA Chapter 5 — PlayerProjection brief

**Phase:** One scorer. **No** board emit. **No** props tags.  
**Depends on:** [#379](https://github.com/kosedge/kosedge/pull/379) merged  
**Stamp:** `wnba-season-engine-v0.1`  
**Residual cap (identity):** `WNBA_TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Grid:** `MINUTE_GRID_SUM = 200`  
**Ch1 shrink:** `WNBA_TEAM_CARRY_SHRINK = 0.85` (**unchanged**)  
**Scorecard:** [`docs/WNBA_CH5_PLAYER_PROJECTION_SCORECARD.md`](./WNBA_CH5_PLAYER_PROJECTION_SCORECARD.md)

---

## What this PR does

One `PlayerProjection` per Ch2 rotation slot (`MIN > 0`):

`MIN USG PTS REB AST STL BLK TOV 3PM PRA PR RA` + **σ each**.

Reads Ch2 talent × Ch2 minutes × team pace / `implied_ppg` from the rebased pack.  
`Σ PTS` identity-scaled to team `implied_ppg` within the Ch2 residual cap.

---

## Allowlist

| Item          | Path                                                      |
| ------------- | --------------------------------------------------------- |
| Schema + pack | `…/data/wnba_player_projection_2026.json`                 |
| Reader        | `player_projection.py`                                    |
| Builder       | `scripts/wnba/build_player_projection_ch5.py`             |
| Tests         | `tests/test_wnba_player_projection_ch5.py` (WNBA-only CI) |
| Docs          | this brief + scorecard                                    |

---

## Forbidden (honored)

- Board emit · props PLAY · new minute grid
- NBA means as the prior · team if · changing `0.85`
- Aug 1 leftover KEI blend · NBA / CFB / NFL packs

---

## Gates

- Every player with `MIN > 0` has the full vector + σ
- `Σ MIN = 200`, `Σ PTS` within residual cap
- σ is computed (season-rate dispersion × MIN), not a hardcoded 4
- CON@ATL market-only row untouched (no board write)
- Leftover fair-line ids `401857105` / `401857106` still listed, not blended
- NBA HOU@OKC still ~−4.2 · CFB BALL@OSU **−40.5**

---

## Done

Pack on disk. Board leftover still leftover.  
**Stop.** Chapter 3 situation next (WNBA-point coeffs, paper-sim). Chapter 4 emit after that. Not props yet.
