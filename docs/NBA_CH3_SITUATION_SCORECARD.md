# NBA Chapter 3 — situation scorecard

**Stamp:** `nba-season-engine-v0.1` · schedule grain `2025-26` · `as_of=2026-09-01`  
**Cap:** `SITUATION_TEAM_PTS_CAP = 3.0`  
**Shrink frozen:** `TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NBA_CH3_SITUATION_BRIEF.md`](./NBA_CH3_SITUATION_BRIEF.md)

---

## Paper-sim (before write)

Schedule: 1200 RS games / 2400 team-games (`nba_schedule_2025_26.json`).

| Class prevalence      |  Rate |
| --------------------- | ----: |
| Home                  | 0.500 |
| B2B (rest=1 ∪ 3-in-4) | 0.316 |
| Travel                | 0.169 |
| Altitude venue        | 0.067 |
| 3-in-4 alone          | 0.270 |

Grid searched: home `{1.5,2.0,2.5}` × B2B `{-1.0,-1.5,-2.0}` × travel `{-0.5,-1.0,-1.5}` × altitude `{0.5,1.0,1.5}`.

**Chosen (clip_rate = 0):**

| Class    |                     Coeff |
| -------- | ------------------------: |
| Home     |                      +2.0 |
| B2B      |                      −1.5 |
| Travel   |                      −0.5 |
| Altitude | +1.0 (± by side at venue) |

PPG′ after Δ: **108.88 – 122.03** (league-sane). Max \|raw\| before clip among chosen = 3.0.

---

## Apply-on-read

```text
team_ppg' = implied_ppg_ch2 + clip(Σ class_coeff, ±3.0)
if Δ ≠ 0: PlayerProjection PTS × (ppg' / Σ PTS)   # copy-through only
```

ORtg / DRtg / pace remain the Ch2 rebased line (situation is not a second net prior).

Altitude venues (flag file only): Ball Arena (Denver, CO); Delta Center (Salt Lake City, UT).

---

## Gates

| Gate                         | Result   |
| ---------------------------- | -------- |
| League-sane PPG′ / ORtg/DRtg | **PASS** |
| Σ PTS within ±3.0            | **PASS** |
| CFB BALL@OSU −40.5           | **PASS** |
| No team name in an `if`      | **PASS** |
| TEAM_CARRY_SHRINK = 0.85     | **PASS** |
| Board untagged               | **PASS** |

---

## Stop

Applied on read. **Next = Chapter 4** (team KEI; PASS until trusted Best). Not Ch6.
