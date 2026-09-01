# NBA Chapter 6 — props dark scorecard

**Stamp:** `nba-season-engine-v0.1` · props `nba-props-ch6-dark-v1`  
**Object SoT:** Ch5 `PlayerProjection` (270)  
**Shrink unchanged:** `TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NBA_CH6_PROPS_DARK_BRIEF.md`](./NBA_CH6_PROPS_DARK_BRIEF.md)

---

## Desk formula

```text
mean_mkt = PlayerProjection[vector]     # PTS / REB / AST / 3PM
σ_game   = f(mean)                      # game-grain; not Ch5 season-rate σ
z        = (mean − line) / σ_game       # display only when line joined
tag      = PASS                         # dark — never PLAY / WATCH
```

Minutes gate: omit `MIN < PROP_MINUTES_GATE` (12.0).

---

## Register (suppressed)

| Gate                      | Value                    | Dark behavior       |
| ------------------------- | ------------------------ | ------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs and `≥ 0.6σ` | counted, not tagged |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                      | unused (play_n=0)   |
| `PROP_MINUTES_GATE`       | `12.0`                   | enforced            |

---

## Gates

| Gate                                     | Result   |
| ---------------------------------------- | -------- |
| Means from Ch5 (not stub rates)          | **PASS** |
| `play_n == 0` on dark board              | **PASS** |
| Huge gap still PASS (`would_clear_play`) | **PASS** |
| Minutes gate                             | **PASS** |
| Publish posture `props=dark`             | **PASS** |
| CFB BALL@OSU −40.5                       | **PASS** |
| `TEAM_CARRY_SHRINK` 0.85                 | **PASS** |
| No Ch1/Ch2/Ch5 rematerialize             | **PASS** |

---

## Does not

PLAY tags · stake · fantasy · second scorer · book-walk · CFB/NFL churn

**Next:** Chapter 7 fantasy scores the same Ch5 object — or Ch9 grades before any PLAY ungate.
