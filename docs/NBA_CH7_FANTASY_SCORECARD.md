# NBA Chapter 7 — fantasy scorecard

**Stamp:** `nba-season-engine-v0.1` · fantasy `nba-fantasy-ch7-v1`  
**Object SoT:** Ch5 `PlayerProjection`  
**Scoring profile:** `kos_default_points`  
**Brief:** [`docs/NBA_CH7_FANTASY_BRIEF.md`](./NBA_CH7_FANTASY_BRIEF.md)

---

## Scoring map (published)

```text
FP = 1.0·PTS + 1.2·REB + 1.5·AST + 3.0·STL + 3.0·BLK − 1.0·TOV + 0.5·3PM
season = FP × 82
cats   = {PTS, REB, AST, STL, BLK, TOV, 3PM} unweighted
```

---

## 10-row star scorecard (opening-night means)

| #   | Player                  | Team |  MIN |  PTS |  REB | AST | FP/G | FP/Szn | Box == Ch5 |
| --- | ----------------------- | ---- | ---: | ---: | ---: | --: | ---: | -----: | ---------- |
| 1   | Victor Wembanyama       | SAS  | 34.0 | 26.5 | 12.6 | 3.9 | 60.4 |   4952 | **PASS**   |
| 2   | Nikola Jokić            | DEN  | 34.0 | 22.8 | 12.2 | 9.8 | 56.1 |   4599 | **PASS**   |
| 3   | Giannis Antetokounmpo   | MIA  | 34.0 | 28.3 | 11.9 | 6.6 | 55.4 |   4544 | **PASS**   |
| 4   | Luka Dončić             | LAL  | 34.0 | 29.4 |  7.6 | 7.9 | 54.4 |   4464 | **PASS**   |
| 5   | Shai Gilgeous-Alexander | OKC  | 34.0 | 30.1 |  4.8 | 6.5 | 51.7 |   4243 | **PASS**   |
| 6   | Anthony Davis           | DAL  | 34.0 | 21.7 | 12.2 | 3.3 | 49.2 |   4037 | **PASS**   |
| 7   | Cade Cunningham         | DET  | 34.0 | 23.5 |  5.4 | 9.1 | 46.5 |   3816 | **PASS**   |
| 8   | Jayson Tatum            | BOS  | 34.0 | 23.9 |  8.8 | 5.2 | 45.8 |   3759 | **PASS**   |
| 9   | LaMelo Ball             | CHA  | 34.0 | 23.1 |  5.4 | 8.2 | 45.4 |   3726 | **PASS**   |
| 10  | Joel Embiid             | PHI  | 34.0 | 23.6 |  9.1 | 4.8 | 45.2 |   3708 | **PASS**   |

Team column follows Ch2 grid / transaction map.

---

## Gates

| Gate                                | Result   |
| ----------------------------------- | -------- |
| Box stats == Ch5 fields             | **PASS** |
| Team Σ PTS max drift ≤ 3.0 (0.0002) | **PASS** |
| Props still dark (no PLAY/LEAN)     | **PASS** |
| No new means / no grid rewrite      | **PASS** |
| CFB BALL@OSU −40.5                  | **PASS** |
| `TEAM_CARRY_SHRINK` 0.85            | **PASS** |

---

## Does not

New scorer · props tags · DFS optimizer · team if · Ch3/Ch4 retune · CFB/NFL

**Stop.** Ch8 chrome or Ch9 grades next — not a tag PR.
