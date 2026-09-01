# WNBA Chapter 6 — props dark scorecard

**Stamp:** `wnba-season-engine-v0.1` · props `wnba-props-ch6-dark-v1`  
**Object SoT:** Ch5 `PlayerProjection` (135)  
**Shrink unchanged:** `WNBA_TEAM_CARRY_SHRINK = 0.85` · grid `200`  
**Brief:** [`docs/WNBA_CH6_PROPS_DARK_BRIEF.md`](./WNBA_CH6_PROPS_DARK_BRIEF.md)

---

## Desk formula

```text
mean   = PlayerProjection[vector]          # Odds-backed only
Best   = trusted book line else —
edge   = mean − Best                       # null when Best cleared
σ_game = f(mean)                           # game-grain
tag    = PASS                              # never PLAY / LEAN
```

Odds-backed: `pts reb ast threes`.  
Odds-missing (not boarded): `PRA` `PR` `RA`.

---

## 8-row star scorecard (Ch5 means)

| Player            | Team |  PTS |  REB | AST | 3PM |  PRA | Tag  |
| ----------------- | ---- | ---: | ---: | --: | --: | ---: | ---- |
| Kelsey Mitchell   | IND  | 22.0 |  1.9 | 2.8 | 2.8 | 26.7 | PASS |
| Dominique Malonga | SEA  | 21.6 | 10.8 | 2.1 | 0.5 | 34.4 | PASS |
| A'ja Wilson       | LAS  | 19.5 | 10.1 | 3.0 | 0.7 | 32.5 | PASS |
| Paige Bueckers    | DAL  | 19.1 |  3.8 | 5.5 | 1.5 | 28.4 | PASS |
| Shakira Austin    | WSH  | 18.2 |  9.7 | 2.3 | 0.3 | 30.3 | PASS |
| Olivia Miles      | MIN  | 18.0 |  4.8 | 6.2 | 1.8 | 29.0 | PASS |
| Napheesa Collier  | MIN  | 17.7 |  7.8 | 3.1 | 1.6 | 28.5 | PASS |
| Chennedy Carter   | LAS  | 17.5 |  3.7 | 2.9 | 1.2 | 24.0 | PASS |

Best / edge columns stay **—** until a trusted `basketball_wnba` join lands. No invented books.  
PRA shown for identity only — **not boarded** (Odds has no PRA key).

---

## Register (suppressed)

| Gate                      | Value                    | Dark behavior       |
| ------------------------- | ------------------------ | ------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs and `≥ 0.6σ` | counted, not tagged |
| `PROP_PLAY_CAP_PER_SLATE` | `4`                      | unused (`play_n=0`) |
| `PROP_MINUTES_GATE`       | `10.0`                   | enforced            |

---

## Gates

| Gate                                | Result   |
| ----------------------------------- | -------- |
| Displayed mean == Ch5 field         | **PASS** |
| No fake book / untrusted Best → —   | **PASS** |
| No PLAY/LEAN string on a prop       | **PASS** |
| Odds PRA/PR/RA not guessed          | **PASS** |
| `play_n == 0` · `lean_n == 0`       | **PASS** |
| Team board unchanged (Ch4 CON@ATL)  | **PASS** |
| Leftovers `401857105`/`106` dropped | **PASS** |
| NBA HOU@OKC ≈ −4.16                 | **PASS** |
| CFB BALL@OSU −40.51                 | **PASS** |
| `WNBA_TEAM_CARRY_SHRINK` 0.85       | **PASS** |

---

## Does not

Tags · new means · new grid · team if · Ch3/Ch4 retune · fantasy · alts · NBA/CFB/NFL

**Stop.** Fantasy is Chapter 7 later and must read this same `PlayerProjection`.
