# NBA Chapter 6 — props dark scorecard

**Stamp:** `nba-season-engine-v0.1` · props `nba-props-ch6-dark-v1`  
**Object SoT:** Ch5 `PlayerProjection` (270)  
**Shrink unchanged:** `TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NBA_CH6_PROPS_DARK_BRIEF.md`](./NBA_CH6_PROPS_DARK_BRIEF.md)

---

## Desk formula

```text
mean   = PlayerProjection[vector]          # Odds-backed only
Best   = trusted book line else —
edge   = mean − Best                       # null when Best cleared
σ_game = f(mean)                           # game-grain
tag    = PASS                              # never PLAY / LEAN
```

Odds-backed: `pts reb ast threes pra`.  
Odds-missing (not boarded): `PR` `RA`.

---

## 10-row star scorecard (Ch5 means — opening night)

| Player                  | Team |  PTS |  REB | AST | 3PM |  PRA | Tag  |
| ----------------------- | ---- | ---: | ---: | --: | --: | ---: | ---- |
| Shai Gilgeous-Alexander | OKC  | 30.1 |  4.8 | 6.5 | 1.8 | 41.4 | PASS |
| Luka Dončić             | LAL  | 29.5 |  7.6 | 7.9 | 3.6 | 44.9 | PASS |
| Giannis Antetokounmpo   | MIA  | 28.3 | 11.9 | 6.6 | 0.4 | 46.9 | PASS |
| Stephen Curry           | GSW  | 26.9 |  4.3 | 5.5 | 4.8 | 36.8 | PASS |
| Victor Wembanyama       | SAS  | 26.5 | 12.6 | 3.9 | 2.5 | 42.9 | PASS |
| Lauri Markkanen         | UTA  | 26.1 |  7.2 | 2.0 | 3.0 | 35.3 | PASS |
| Donovan Mitchell        | CLE  | 25.7 |  4.7 | 5.7 | 3.3 | 36.1 | PASS |
| Anthony Edwards         | MIN  | 25.5 |  5.1 | 4.1 | 3.3 | 34.7 | PASS |
| Jalen Brunson           | NYK  | 25.4 |  3.1 | 6.5 | 2.4 | 35.0 | PASS |
| Zion Williamson         | NOP  | 24.8 |  7.1 | 4.8 | 0.1 | 36.7 | PASS |

Best / edge columns stay **—** until a trusted `basketball_nba` join lands. No invented books.

---

## Register (suppressed)

| Gate                      | Value                    | Dark behavior       |
| ------------------------- | ------------------------ | ------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs and `≥ 0.6σ` | counted, not tagged |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                      | unused (`play_n=0`) |
| `PROP_MINUTES_GATE`       | `12.0`                   | enforced            |

---

## Gates

| Gate                              | Result   |
| --------------------------------- | -------- |
| Displayed mean == Ch5 field       | **PASS** |
| No fake book / untrusted Best → — | **PASS** |
| No PLAY/LEAN string on a prop     | **PASS** |
| Odds PR/RA not guessed            | **PASS** |
| `play_n == 0` · `lean_n == 0`     | **PASS** |
| Team board unchanged (Ch4)        | **PASS** |
| CFB BALL@OSU −40.5                | **PASS** |
| `TEAM_CARRY_SHRINK` 0.85          | **PASS** |

---

## Does not

Tags · new means · new grid · team if · Ch3/Ch4 retune · fantasy · alts · CFB/NFL

**Stop.** Tags are a later PR. Chapter 7 fantasy must read this same `PlayerProjection`.
