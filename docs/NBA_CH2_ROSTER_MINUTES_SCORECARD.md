# NBA Chapter 2 — roster × minutes scorecard

**Stamp:** `nba-season-engine-v0.1` · `as_of=2026-09-01` · carry → `2026-27`  
**Weights:** `PLAYER_YEAR_WEIGHTS = 0.20 / 0.30 / 0.50`  
**Residual cap:** `TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Ch1 shrink (unchanged):** `TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NBA_CH2_ROSTER_MINUTES_BRIEF.md`](./NBA_CH2_ROSTER_MINUTES_BRIEF.md)

---

## Formula

```text
talent = Σ_y w_y · BPM_y   (renormalized over available seasons)
player_net = Σ (talent × minutes) / 240
residual = clip(ch1_net − player_net, ±3.0)
team_net = player_net + residual
```

Minute grid v0 class: star×2 @ 34, starter×3 @ 30, bench×4 residual → **240**.

---

## Transaction map (stars move with the map)

| Player                | From | To  | Note                                       |
| --------------------- | ---- | --- | ------------------------------------------ |
| LeBron James          | LAL  | PHI | FA: LeBron James → 76ers                   |
| Giannis Antetokounmpo | MIL  | MIA | Trade: Giannis Bucks → Heat                |
| Bobby Portis          | MIL  | MIA | Trade: Portis with Giannis → Heat          |
| Jaylen Brown          | BOS  | PHI | Trade: Jaylen Brown Celtics → 76ers        |
| Paul George           | PHI  | BOS | Trade: Paul George in Brown deal → Celtics |
| Kawhi Leonard         | LAC  | TOR | Trade: Kawhi Clippers → Raptors            |
| Walker Kessler        | UTA  | LAL | S&T: Walker Kessler Jazz → Lakers          |
| Tyler Herro           | MIA  | MIL | Trade return: Herro Heat → Bucks           |
| Kel'el Ware           | MIA  | MIL | Trade return: Ware Heat → Bucks            |
| Jaime Jaquez Jr.      | MIA  | MIL | Trade return: Jaquez Heat → Bucks          |
| DeMar DeRozan         | SAC  | DEN | FA: DeMar DeRozan → Nuggets                |
| Klay Thompson         | DAL  | MIA | FA: Klay Thompson → Heat                   |

Rotation note: Klay Thompson is on the MIA **roster** via the map but outside the 9-man class grid (talent BPM < rotation cut). He does **not** appear on DAL.

---

## Top movers vs Ch1 shell (|Δ net|)

| Team | Ch1 net | Player net | Residual | Rebased net |     Δ |
| ---- | ------: | ---------: | -------: | ----------: | ----: |
| WAS  |  -10.06 |      -0.88 |    -3.00 |       -3.88 | +6.18 |
| BKN  |   -8.73 |      -0.40 |    -3.00 |       -3.40 | +5.33 |
| SAC  |   -8.56 |      -0.36 |    -3.00 |       -3.36 | +5.20 |
| IND  |   -6.77 |       0.64 |    -3.00 |       -2.36 | +4.41 |
| UTA  |   -6.98 |       0.35 |    -3.00 |       -2.65 | +4.32 |
| MEM  |   -5.01 |       1.71 |    -3.00 |       -1.29 | +3.73 |
| MIL  |   -5.52 |       0.22 |    -3.00 |       -2.78 | +2.73 |
| OKC  |    9.39 |       3.78 |     3.00 |        6.78 | -2.61 |
| DAL  |   -4.62 |       0.76 |    -3.00 |       -2.24 | +2.38 |
| DET  |    7.00 |       1.92 |     3.00 |        4.92 | -2.07 |

---

## Rebased board (by net)

|  Rk | Team |   Net |  ORtg |  DRtg |  Pace |  PPG′ | Min Σ |
| --: | ---- | ----: | ----: | ----: | ----: | ----: | ----: |
|   1 | OKC  |  6.78 | 119.2 | 112.5 |  99.3 | 118.4 |   240 |
|   2 | BOS  |  5.31 | 118.5 | 113.2 |  95.5 | 113.2 |   240 |
|   3 | SAS  |  5.14 | 118.4 | 113.3 |  99.8 | 118.2 |   240 |
|   4 | DET  |  4.92 | 118.3 | 113.4 |  99.3 | 117.5 |   240 |
|   5 | NYK  |  4.64 | 118.2 | 113.5 |  97.2 | 114.8 |   240 |
|   6 | HOU  |  4.58 | 118.1 | 113.6 |  96.6 | 114.1 |   240 |
|   7 | DEN  |  4.39 | 118.0 | 113.6 |  98.5 | 116.3 |   240 |
|   8 | CHA  |  4.28 | 118.0 | 113.7 |  97.2 | 114.7 |   240 |
|   9 | CLE  |  3.44 | 117.6 | 114.1 |  99.8 | 117.3 |   240 |
|  10 | MIN  |  2.62 | 117.2 | 114.5 | 100.3 | 117.5 |   240 |
|  11 | TOR  |  2.19 | 116.9 | 114.7 |  98.5 | 115.2 |   240 |
|  12 | ATL  |  2.01 | 116.8 | 114.8 | 101.3 | 118.4 |   240 |
|  13 | MIA  |  1.85 | 116.8 | 114.9 | 102.8 | 120.0 |   240 |
|  14 | LAL  |  1.48 | 116.6 | 115.1 |  98.5 | 114.8 |   240 |
|  15 | PHX  |  1.21 | 116.4 | 115.2 |  97.5 | 113.6 |   240 |
|  16 | LAC  |  0.96 | 116.3 | 115.4 |  96.9 | 112.8 |   240 |
|  17 | ORL  |  0.48 | 116.1 | 115.6 |  99.9 | 116.0 |   240 |
|  18 | PHI  | -0.14 | 115.8 | 115.9 |  99.4 | 115.1 |   240 |
|  19 | POR  | -0.14 | 115.8 | 115.9 | 100.3 | 116.2 |   240 |
|  20 | GSW  | -0.47 | 115.6 | 116.1 |  99.1 | 114.5 |   240 |
|  21 | MEM  | -1.29 | 115.2 | 116.5 | 101.0 | 116.4 |   240 |
|  22 | DAL  | -2.24 | 114.7 | 117.0 | 101.3 | 116.3 |   240 |
|  23 | IND  | -2.36 | 114.7 | 117.0 | 100.8 | 115.5 |   240 |
|  24 | NOP  | -2.38 | 114.7 | 117.0 | 100.2 | 114.8 |   240 |
|  25 | CHI  | -2.57 | 114.6 | 117.1 | 102.0 | 116.9 |   240 |
|  26 | UTA  | -2.65 | 114.5 | 117.2 | 101.9 | 116.6 |   240 |
|  27 | MIL  | -2.78 | 114.5 | 117.2 |  97.9 | 112.0 |   240 |
|  28 | SAC  | -3.36 | 114.2 | 117.5 |  99.2 | 113.3 |   240 |
|  29 | BKN  | -3.40 | 114.1 | 117.5 |  97.4 | 111.2 |   240 |
|  30 | WAS  | -3.88 | 113.9 | 117.8 | 101.1 | 115.2 |   240 |

Implied PPG range: **111.22–120.03** (no 140-possession ghosts).

---

## Gates

| Gate                             | Result   |
| -------------------------------- | -------- |
| 30 × 240 minutes                 | **PASS** |
| PPG sanity                       | **PASS** |
| Residual ≤ ±3.0                  | **PASS** |
| Movers leave old grid            | **PASS** |
| TEAM_CARRY_SHRINK unchanged 0.85 | **PASS** |
| CFB BALL@OSU −40.5               | **PASS** |
| No futures / tags / props        | **PASS** |

Board still untagged. Chapter 5 (`PlayerProjection`) is next ratings work — not Chapter 6 props.
