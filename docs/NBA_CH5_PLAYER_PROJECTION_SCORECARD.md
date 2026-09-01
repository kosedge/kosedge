# NBA Chapter 5 — PlayerProjection scorecard

**Stamp:** `nba-season-engine-v0.1` · `as_of=2026-09-01` · season `2026-27`  
**Object:** `PlayerProjection` (270 = 30 × 9)  
**Residual / identity cap:** `TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Shrink unchanged:** `TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NBA_CH5_PLAYER_PROJECTION_BRIEF.md`](./NBA_CH5_PLAYER_PROJECTION_BRIEF.md)

---

## Formula

```text
rate_y = stat_per_g / mp_per_g
rate   = Σ_y w_y · rate_y          (w = 0.20 / 0.30 / 0.50; renormalized)
raw    = rate × MIN × (team_pace / league_pace)
PTS_i  = raw_PTS_i × (implied_ppg / Σ raw_PTS)
σ_rate = pstdev({rate_y}) or 0.15·|rate| if single season
σ_stat = σ_rate × MIN × pace_scale   (PTS σ also × identity scale)
PRA/PR/RA means = sums; σ = √(Σ component σ²)
```

Opening-night minutes from Ch2 class grid. Opponent grain = league-average (no B2B / travel — Ch3).

---

## Sample stars

| Player                  | Team |  MIN |  PTS |  REB |  AST |  USG | σPTS |
| ----------------------- | ---- | ---: | ---: | ---: | ---: | ---: | ---: |
| Shai Gilgeous-Alexander | OKC  | 34.0 | 30.1 |  4.8 |  6.5 | 33.7 | 0.96 |
| Luka Dončić             | LAL  | 34.0 | 29.4 |  7.6 |  7.9 | 36.4 | 1.98 |
| Giannis Antetokounmpo   | MIA  | 34.0 | 28.3 | 11.9 |  6.6 | 35.7 | 1.19 |
| Stephen Curry           | GSW  | 34.0 | 26.9 |  4.3 |  5.5 | 31.4 | 1.34 |
| Jayson Tatum            | BOS  | 34.0 | 23.9 |  8.8 |  5.2 | 30.4 | 1.24 |
| Nikola Jokić            | DEN  | 34.0 | 22.8 | 12.2 |  9.8 | 29.9 | 0.53 |
| Tyrese Haliburton       | IND  | 34.0 | 19.1 |  3.8 | 10.3 | 22.8 | 1.16 |
| LeBron James            | PHI  | 34.0 | 18.2 |  6.8 |  7.7 | 28.5 | 1.12 |

Team column follows Ch2 grid / transaction map (not a Ch5 team-if).

---

## Team-sum check

| Gate                     | Result                                      |
| ------------------------ | ------------------------------------------- |
| 30 teams × `Σ MIN = 240` | **PASS**                                    |
| `Σ PTS` vs `implied_ppg` | **PASS** — max \|drift\| = **0.0002** ≪ 3.0 |
| Residual cap             | **3.0** (registered)                        |
| σ hardcoded 4            | **FAIL avoided** — 0 / 2970 σ values == 4   |

---

## Gates

| Gate                                   | Result   |
| -------------------------------------- | -------- |
| Full vector + σ for every MIN>0        | **PASS** |
| Σ MIN = 240, Σ PTS within residual cap | **PASS** |
| σ computed, not hardcoded 4            | **PASS** |
| CFB BALL@OSU −40.5                     | **PASS** |
| Zero prop tag fields                   | **PASS** |
| TEAM_CARRY_SHRINK unchanged 0.85       | **PASS** |

Props still dark. Chapter 6 desks this object — does not re-score it.
