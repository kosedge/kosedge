# NHL Chapter 6 — props dark scorecard

**Stamp:** `nhl-season-engine-v0.1` · props `nhl-props-ch6-dark-v1`  
**Object SoT:** Ch5 `PlayerProjection` (576 skaters · 126 goalies)  
**Shrink unchanged:** `NHL_TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NHL_CH6_PROPS_DARK_BRIEF.md`](./NHL_CH6_PROPS_DARK_BRIEF.md)

---

## Desk formula

```text
mean   = PlayerProjection[vector]          # Odds-backed skaters
Best   = trusted book line else —
edge   = mean − Best                       # null when Best cleared
σ_game = f(mean)                           # game-grain
tag    = PASS                              # never PLAY / LEAN
```

Odds-backed: `goals assists pts sog`.  
Goalie `SAVES`: starter-unknown → Best **—** (`STARTER_GATE = unknown`).

---

## 10-row star scorecard (Ch5 means)

| Player            | Team |    G |    A |    P |  SOG | Tag  |
| ----------------- | ---- | ---: | ---: | ---: | ---: | ---- |
| Nikita Kucherov   | TBL  | 0.54 | 1.05 | 1.59 | 3.03 | PASS |
| Connor McDavid    | EDM  | 0.51 | 1.04 | 1.56 | 3.13 | PASS |
| Macklin Celebrini | SJS  | 0.78 | 0.66 | 1.44 | 3.10 | PASS |
| Leon Draisaitl    | EDM  | 0.61 | 0.79 | 1.40 | 2.71 | PASS |
| Nathan MacKinnon  | COL  | 0.48 | 0.92 | 1.40 | 4.04 | PASS |
| David Pastrnak    | BOS  | 0.58 | 0.80 | 1.38 | 3.61 | PASS |
| Sidney Crosby     | PIT  | 0.64 | 0.62 | 1.26 | 2.48 | PASS |
| William Nylander  | TOR  | 0.57 | 0.61 | 1.18 | 2.68 | PASS |
| Kirill Kaprizov   | MIN  | 0.61 | 0.57 | 1.18 | 3.12 | PASS |
| Jack Hughes       | NJD  | 0.43 | 0.71 | 1.14 | 3.55 | PASS |

Best / edge columns stay **—** until a trusted `icehockey_nhl` join lands. No invented books.  
(1-GP rate spikes like Bonk stay in the warehouse but are omitted from the star card.)

---

## Goalie dash (STARTER_GATE unknown)

| Role         | Behavior                                  |
| ------------ | ----------------------------------------- |
| Goalie SAVES | Proj from Ch5 · Best **—** · Tag **PASS** |
| PLAY / LEAN  | Never — dark + starter gate               |

---

## Register (suppressed)

| Gate                      | Value                    | Dark behavior       |
| ------------------------- | ------------------------ | ------------------- |
| `PROP_PLAY`               | `≥ 4.0` abs and `≥ 0.6σ` | counted, not tagged |
| `PROP_PLAY_CAP_PER_SLATE` | `6`                      | unused (`play_n=0`) |
| `PROP_TOI_GATE`           | `8.0`                    | enforced            |
| `STARTER_GATE`            | `unknown`                | goalie Best —       |

---

## Gates

| Gate                               | Result   |
| ---------------------------------- | -------- |
| Displayed mean == Ch5 field        | **PASS** |
| No fake book / untrusted Best → —  | **PASS** |
| No PLAY/LEAN string on a prop      | **PASS** |
| Goalie starter-unknown rows stay — | **PASS** |
| `play_n == 0` · `lean_n == 0`      | **PASS** |
| Ch4 FLA@CAR puck −0.94 unchanged   | **PASS** |
| NBA / WNBA / CFB untouched         | **PASS** |
| `NHL_TEAM_CARRY_SHRINK` 0.85       | **PASS** |

---

## Does not

Tags · new means · new TOI · team if · Ch3/Ch4 retune · fantasy · inventing Odds saves

**Stop.** After screenshot. Chapter 7 fantasy is queued and must read this same `PlayerProjection`.
