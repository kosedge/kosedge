# WNBA Chapter 7 — fantasy scorecard

**Stamp:** `wnba-season-engine-v0.1` · fantasy `wnba-fantasy-ch7-v1`  
**Object SoT:** Ch5 `PlayerProjection` (135)  
**Scoring profile:** `kos_default_points` · season × **40**  
**Brief:** [`docs/WNBA_CH7_FANTASY_BRIEF.md`](./WNBA_CH7_FANTASY_BRIEF.md)

---

## Scoring map (published)

```text
FP = 1.0·PTS + 1.2·REB + 1.5·AST + 3.0·STL + 3.0·BLK − 1.0·TOV + 0.5·3PM
season = FP × 40
cats   = {PTS, REB, AST, STL, BLK, TOV, 3PM} unweighted
```

---

## 8-row star scorecard (Ch5 means)

| #   | Player            | Team |  MIN |  PTS |  REB | AST | STL | BLK | TOV | 3PM | FP/G | FP/Szn | Box == Ch5 |
| --- | ----------------- | ---- | ---: | ---: | ---: | --: | --: | --: | --: | --: | ---: | -----: | ---------- |
| 1   | A'ja Wilson       | LAS  | 32.0 | 19.5 | 10.1 | 3.0 | 1.5 | 2.2 | 2.2 | 0.7 | 45.4 |   1816 | **PASS**   |
| 2   | Dominique Malonga | SEA  | 32.0 | 21.6 | 10.8 | 2.1 | 1.0 | 1.7 | 3.0 | 0.5 | 43.2 |   1728 | **PASS**   |
| 3   | Aliyah Boston     | IND  | 32.0 | 17.3 |  9.5 | 3.7 | 1.5 | 1.3 | 2.4 | 0.7 | 40.5 |   1620 | **PASS**   |
| 4   | Napheesa Collier  | MIN  | 32.0 | 17.7 |  7.8 | 3.1 | 1.6 | 1.2 | 2.2 | 1.6 | 38.6 |   1544 | **PASS**   |
| 5   | Alyssa Thomas     | PHX  | 32.0 | 14.0 |  8.0 | 8.4 | 1.5 | 0.4 | 3.4 | 0.0 | 38.4 |   1536 | **PASS**   |
| 6   | Angel Reese       | ATL  | 32.0 | 14.7 | 12.9 | 3.0 | 1.6 | 0.7 | 3.3 | 0.2 | 38.3 |   1532 | **PASS**   |
| 7   | Breanna Stewart   | NY   | 32.0 | 17.4 |  7.6 | 3.3 | 1.4 | 1.4 | 1.9 | 0.8 | 38.3 |   1531 | **PASS**   |
| 8   | Shakira Austin    | WSH  | 32.0 | 18.2 |  9.7 | 2.3 | 1.2 | 1.4 | 3.3 | 0.3 | 38.3 |   1530 | **PASS**   |

Slate view = same players, same means, same sort.

---

## Gates

| Gate                                | Result   |
| ----------------------------------- | -------- |
| Box stats == Ch5 fields             | **PASS** |
| Σ MIN = 200 per team                | **PASS** |
| Team Σ PTS max drift ≤ 3.0 (0.0002) | **PASS** |
| Props still dark (no PLAY/LEAN)     | **PASS** |
| No new means / no grid rewrite      | **PASS** |
| NBA fantasy module unchanged        | **PASS** |
| CFB BALL@OSU −40.5                  | **PASS** |
| `WNBA_TEAM_CARRY_SHRINK` 0.85       | **PASS** |

---

## Does not

New scorer · props tags · DFS optimizer · team if · Ch3/Ch4 retune · NBA/CFB/NFL · 15 team previews

**Stop.** Chapter 9 grades (schema + empty store) before playoffs Sep 27 — **not** a tag PR.
