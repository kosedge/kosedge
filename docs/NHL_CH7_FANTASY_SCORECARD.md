# NHL Chapter 7 — fantasy scorecard

**Stamp:** `nhl-season-engine-v0.1` · fantasy `nhl-fantasy-ch7-v1`  
**Object SoT:** Ch5 `PlayerProjection` (576 skaters · 126 goalies)  
**Scoring profile:** `kos_default_points`  
**Brief:** [`docs/NHL_CH7_FANTASY_BRIEF.md`](./NHL_CH7_FANTASY_BRIEF.md)

---

## Scoring map (published)

```text
FP_skater = 3.0·G + 2.0·A + 0.4·SOG
FP_goalie = 0.2·SAVES
season    = FP × 82
cats      = {G, A, P, SOG} skater · {start_share, SV_pct, SA, GAA, SAVES} goalie
```

`P` shown unweighted. No invented goalie wins.

---

## 10-row star scorecard (opening-night means)

| #   | Player            | Team |    G |    A |  SOG | FP/G | FP/Szn | Box == Ch5 |
| --- | ----------------- | ---- | ---: | ---: | ---: | ---: | -----: | ---------- |
| 1   | Nikita Kucherov   | TBL  | 0.54 | 1.05 | 3.03 | 4.94 |    405 | **PASS**   |
| 2   | Macklin Celebrini | SJS  | 0.78 | 0.66 | 3.10 | 4.89 |    401 | **PASS**   |
| 3   | Nathan MacKinnon  | COL  | 0.48 | 0.92 | 4.04 | 4.89 |    401 | **PASS**   |
| 4   | Connor McDavid    | EDM  | 0.51 | 1.04 | 3.13 | 4.87 |    400 | **PASS**   |
| 5   | David Pastrnak    | BOS  | 0.58 | 0.80 | 3.61 | 4.77 |    392 | **PASS**   |
| 6   | Leon Draisaitl    | EDM  | 0.61 | 0.79 | 2.71 | 4.50 |    369 | **PASS**   |
| 7   | Auston Matthews   | TOR  | 0.62 | 0.48 | 3.69 | 4.30 |    352 | **PASS**   |
| 8   | Kirill Kaprizov   | MIN  | 0.61 | 0.57 | 3.12 | 4.22 |    346 | **PASS**   |
| 9   | Sidney Crosby     | PIT  | 0.64 | 0.62 | 2.48 | 4.15 |    340 | **PASS**   |
| 10  | Jack Hughes       | NJD  | 0.43 | 0.71 | 3.55 | 4.13 |    339 | **PASS**   |

(1-GP rate spikes like Bonk stay in the warehouse but are omitted from the star card.)  
Goalies appear on the board via SAVES (not as skaters); they do not crack this top-10 skater card.

---

## Gates

| Gate                                      | Result   |
| ----------------------------------------- | -------- |
| Box stats == Ch5 fields                   | **PASS** |
| Goalie start_share Σ ≈ 1.0 / team         | **PASS** |
| Team Σ G max drift ≤ 0.15 (~0.0003)       | **PASS** |
| Props still dark (no PLAY/LEAN)           | **PASS** |
| KEINHL FLA@CAR puck −0.94 · total 6.71    | **PASS** |
| `NHL_TEAM_CARRY_SHRINK` 0.85              | **PASS** |
| NBA / WNBA fantasy versions unchanged     | **PASS** |

---

## Does not

New G/A/SOG · new TOI · props tags · DFS optimizer · Ch3/Ch4 retune · invented wins · other sports

**Stop.** Chapter 9 grades before opening night Sep 29 — not a tag PR, not 32 previews until camps (~Sep 16).
