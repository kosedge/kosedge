# WNBA Chapter 2 — roster × minutes scorecard

**Stamp:** `wnba-season-engine-v0.1` · `as_of=2026-09-01` · season `2026`  
**Weights:** `PLAYER_YEAR_WEIGHTS = 0.20 / 0.30 / 0.50`  
**Residual cap:** `WNBA_TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Ch1 shrink (unchanged):** `WNBA_TEAM_CARRY_SHRINK = 0.85`  
**PPG′ band (registered):** **75–91** (WNBA neighborhood ~75–90; not NBA 111–120)  
**Brief:** [`docs/WNBA_CH2_ROSTER_MINUTES_BRIEF.md`](./WNBA_CH2_ROSTER_MINUTES_BRIEF.md)

---

## Formula

```text
talent = Σ_y w_y · (PER_y − 15)   (renormalized over available seasons)
player_net = Σ (talent × minutes) / 200
residual = clip(ch1_net − player_net, ±3.0)
team_net = player_net + residual
```

Minute grid v0 class: star×2 @ 32, starter×3 @ 27, bench×4 residual → **200**.  
(BPM not published on BR WNBA advanced — `PER − 15` is the rate SoT.)

Roster seed = **2026 YTD** primary team (midseason). Expansion-only players (only 2026 seasons) stay on **TOR / POR**.

---

## Expansion-only on grid (stay TOR/POR)

| Team | Expansion-only on 9-man grid                                             |
| ---- | ------------------------------------------------------------------------ |
| TOR  | Kiki Rice (star), Laura Juškaitė (bench), Maria Conde (bench)            |
| POR  | Jordan Harrison (starter), Serah Williams (bench), Frieda Bühner (bench) |

Veterans on TOR/POR (Sykes, Mabrey, Okonkwo, …) are **not** expansion-only — they carry 2024/2025 weight.

---

## Top movers vs Ch1 shell (|Δ net|)

| Team | Ch1 net | Player net | Residual | Rebased net |     Δ |
| ---- | ------: | ---------: | -------: | ----------: | ----: |
| CON  |   -9.34 |       0.21 |    -3.00 |       -2.79 | +6.56 |
| TOR  |   -8.07 |       0.32 |    -3.00 |       -2.68 | +5.39 |
| GSV  |    8.17 |       0.61 |     3.00 |        3.61 | -4.56 |
| LA   |   -4.67 |       1.59 |    -3.00 |       -1.41 | +3.26 |
| SEA  |   -5.69 |       0.11 |    -3.00 |       -2.89 | +2.80 |
| POR  |   -4.84 |       0.73 |    -3.00 |       -2.27 | +2.57 |
| MIN  |    8.51 |       4.03 |     3.00 |        7.03 | -1.48 |
| CHI  |   -3.05 |       1.38 |    -3.00 |       -1.62 | +1.44 |

---

## Rebased board (by net)

|  Rk | Team |   Net |  ORtg |  DRtg | Pace | PPG′ | Min Σ |
| --: | ---- | ----: | ----: | ----: | ---: | ---: | ----: |
|   1 | MIN  |  7.03 | 112.8 | 105.7 | 79.2 | 89.3 |   200 |
|   2 | IND  |  5.39 | 112.0 | 106.6 | 80.9 | 90.6 |   200 |
|   3 | ATL  |  5.34 | 112.0 | 106.6 | 80.4 | 90.0 |   200 |
|   4 | LAS  |  4.34 | 111.5 | 107.1 | 79.4 | 88.5 |   200 |
|   5 | DAL  |  4.00 | 111.3 | 107.2 | 78.4 | 87.3 |   200 |
|   6 | GSV  |  3.61 | 111.1 | 107.4 | 75.2 | 83.5 |   200 |
|   7 | NY   |  3.15 | 110.9 | 107.7 | 79.0 | 87.5 |   200 |
|   8 | WSH  | -0.25 | 109.2 | 109.4 | 77.5 | 84.6 |   200 |
|   9 | LA   | -1.41 | 108.6 | 110.0 | 81.1 | 88.0 |   200 |
|  10 | CHI  | -1.62 | 108.5 | 110.1 | 81.3 | 88.2 |   200 |
|  11 | POR  | -2.27 | 108.2 | 110.4 | 78.6 | 85.0 |   200 |
|  12 | PHX  | -2.48 | 108.0 | 110.5 | 79.0 | 85.4 |   200 |
|  13 | TOR  | -2.68 | 107.9 | 110.6 | 79.4 | 85.7 |   200 |
|  14 | CON  | -2.79 | 107.9 | 110.6 | 79.2 | 85.5 |   200 |
|  15 | SEA  | -2.89 | 107.8 | 110.7 | 80.1 | 86.4 |   200 |

PPG′ observed **83.5–90.6** inside registered **75–91**.

---

## Gates

| Gate                                | Result                    |
| ----------------------------------- | ------------------------- |
| 15 teams × 200 minutes              | **PASS**                  |
| PPG′ in 75–91                       | **PASS** (max 90.6 IND)   |
| Residual within ±3.0                | **PASS**                  |
| Expansion-only stay TOR/POR         | **PASS**                  |
| `WNBA_TEAM_CARRY_SHRINK` still 0.85 | **PASS**                  |
| Live CON@ATL market untouched       | **PASS** (no board write) |
| NBA HOU@OKC still ~−4.2             | **PASS** (`−4.16`)        |
| CFB BALL@OSU still −40.5            | **PASS** (`−40.51`)       |
| Aug-1 leftovers not blended         | **PASS**                  |

Board leftover (LAS@CHI / NY@PHX Aug-1 finals) remains leftover.  
**Stop.** Chapter 5 (`PlayerProjection`) is next — not Ch4 board emit.
