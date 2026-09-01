# WNBA Chapter 2 — roster × minutes brief

**Phase:** Rebase the Ch1 shell onto 2026 players. **No** board emit. **No** props.  
**Depends on:** [#378](https://github.com/kosedge/kosedge/pull/378) merged  
**Stamp:** `wnba-season-engine-v0.1`  
**Weights:** `PLAYER_YEAR_WEIGHTS = 0.20 / 0.30 / 0.50` (2024 / 2025 / 2026-YTD)  
**Grid:** `MINUTE_GRID_SUM = 200` (40×5) — **not** 240  
**Residual cap:** `WNBA_TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Ch1 shrink:** `WNBA_TEAM_CARRY_SHRINK = 0.85` (**unchanged**)  
**Scorecard:** [`docs/WNBA_CH2_ROSTER_MINUTES_SCORECARD.md`](./WNBA_CH2_ROSTER_MINUTES_SCORECARD.md)

---

## What this PR does

1. 3-year decayed player talent for everyone on a 2026 roster (`talent = PER − 15`; BPM not on BR WNBA advanced).
2. Minute grid per team = **200**. Class grid (star 30–34 mid 32, starter 24–30 mid 27, bench residual) — not 15 handwritten teams; **not** NBA classes as-is.
3. Team rating rebases to `Σ(player × minutes)`; Ch1 shrink becomes a **residual cap**, not a second full prior.
4. Scorecard: movers; expansion-only players stay on TOR/POR.

---

## Allowlist

| Item                 | Path                                                   |
| -------------------- | ------------------------------------------------------ |
| Player snapshot (3y) | `…/data/wnba_player_talent_3y_2026.json`               |
| Minutes grid         | `…/data/wnba_minutes_grid_2026.json`                   |
| Rebased teams        | `…/data/wnba_team_prior_rebased_2026.json`             |
| Reader + constants   | `roster_minutes.py` · `priors.py`                      |
| Rebuild              | `scripts/wnba/build_roster_minutes_ch2.py`             |
| Tests                | `tests/test_wnba_roster_minutes_ch2.py` (WNBA-only CI) |
| Docs                 | this brief + scorecard                                 |

---

## Forbidden (honored)

- Board emit · props · copying NBA minute classes as-is
- Team `if` · changing `0.85` · blending Aug 1 leftover KEI
- NBA / CFB / NFL packs

---

## Gates

- 15 teams × 200 minutes
- PPG′ in WNBA-sane band **75–91** (neighborhood ~75–90; observed max 90.6)
- Residual vs Ch1 within **±3.0**
- CON@ATL market-only row untouched
- NBA HOU@OKC still ~−4.2 · CFB −40.5

---

## Done

Grids + rebased table on disk. Board leftover still leftover.  
**Stop.** Chapter 5 (`PlayerProjection`, vector + σ) is next. Not Ch4 emit until that object exists.
