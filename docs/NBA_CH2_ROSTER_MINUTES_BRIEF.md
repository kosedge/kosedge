# NBA Chapter 2 — roster × minutes brief

**Phase:** Rebase the team shell onto 2026–27 players. **No** KEI tags, **no** props desk.  
**Depends on:** [#364](https://github.com/kosedge/kosedge/pull/364) merged  
**Stamp:** `nba-season-engine-v0.1`  
**Weights:** `PLAYER_YEAR_WEIGHTS = 0.20 / 0.30 / 0.50` (23–24 / 24–25 / 25–26)  
**Residual cap:** `TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Ch1 shrink:** `TEAM_CARRY_SHRINK = 0.85` (**unchanged**)  
**Scorecard:** [`docs/NBA_CH2_ROSTER_MINUTES_SCORECARD.md`](./NBA_CH2_ROSTER_MINUTES_SCORECARD.md)

---

## What this PR does

1. 3-year decayed player talent (BPM) for everyone on a 2026–27 roster.
2. Opening-night minute grid per team — class grid, sums to **240**.
3. Team rating rebases to `Σ(player × minutes)`; Ch1 shrink is a **residual cap**, not a second full prior.
4. Scorecard: 30 teams, top movers, transaction stars on the new club only.

---

## Allowlist

| Item                 | Path                                                      |
| -------------------- | --------------------------------------------------------- |
| Player snapshot (3y) | `…/data/nba_player_talent_3y_2026.json`                   |
| Minutes grid         | `…/data/nba_minutes_grid_2026.json`                       |
| Transaction map      | `…/data/nba_transactions_2026.json`                       |
| Rebased teams        | `…/data/nba_team_prior_rebased_2026_27.json`              |
| Reader + constants   | `roster_minutes.py` · `priors.py`                         |
| Rebuild              | `scripts/nba/build_roster_minutes_ch2.py`                 |
| Tests                | `tests/test_nba_roster_minutes_ch2.py` (NBA-only CI path) |
| Docs                 | this brief + scorecard                                    |

Minute grid v0 is a **class grid** (star 32–36 mid 34, starter 28–32 mid 30, bench residual). Offseason movers are **one transaction map**, not `if team ==`.

**Season rows:** prefer BR combined markers (`TOT` / `2TM` / `3TM` / `4TM`); never sum splits with the total.  
**Roster carry:** 2025–26 primary team + players who logged ≥ `MIN_SEASON_MP` in 2024–25 but missed 2025–26 entirely (injury / absence) → last-known franchise. Class rule, not team-if (Haliburton → IND).

---

## Forbidden (honored)

- Props / fantasy scorer · Edge PLAY/LEAN · DARKO/EPM/CTG
- Team `if` / Finals bump · changing `TEAM_CARRY_SHRINK`
- CFB/NFL content · situation/B2B (Ch3) · fixing NFL camp dates

---

## Gates

- 30 teams × 240 minutes
- League-wide points ≈ 82-game pace sanity (PPG′ ~111–120)
- Team residual vs Ch1 within **±3.0** net
- Players who changed teams leave the old grid
- CFB BALL@OSU still **−40.5**
- No futures rewrite

---

## Done

Grids + rebased team table on disk. Board still untagged.  
**Stop.** Chapter 5 (`PlayerProjection`) is next ratings work. Chapter 6 props still waits on that object.
