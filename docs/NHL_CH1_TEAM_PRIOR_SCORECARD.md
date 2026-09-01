# NHL Chapter 1 — team prior scorecard

**Stamp:** `nhl-season-engine-v0.1` · season `2025-26` → carry `2026-27`  
**Chosen:** `NHL_TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/NHL_CH1_TEAM_PRIOR_BRIEF.md`](./NHL_CH1_TEAM_PRIOR_BRIEF.md)  
**Pack:** `services/model-service/src/services/nhl_season_engine/data/nhl_team_prior_2026.json`  
**Source:** `nhl_team_box_2025.json` only (official `*.nhle.com`)

---

## Paper-sim (`s` set)

|                 s | mean net post | net σ pre→post  | COL net′ | VAN net′ | lottery in top-5 |
| ----------------: | ------------: | --------------- | -------: | -------: | ---------------- |
|              0.70 |           0.0 | 40.5393→28.3775 |    69.30 |   -70.00 | none             |
|              0.80 |           0.0 | 40.5393→32.4315 |    79.20 |   -80.00 | none             |
| 0.85 **← chosen** |           0.0 | 40.5393→34.4584 |    84.15 |   -85.00 | none             |
|              0.90 |           0.0 | 40.5393→36.4854 |    89.10 |   -90.00 | none             |

Affine shrink with `s∈(0,1]` preserves rank order. No lottery club (worst-10 by points) enters the post-shrink top-5 at any candidate `s`.

**Pick rationale:** 0.85 — order-preserving, modest compression of full 2025–26 RS box. Own name `NHL_TEAM_CARRY_SHRINK` (not NBA/WNBA).

---

## League means

| Metric     |     Pre | Post (s=0.85) |
| ---------- | ------: | ------------: |
| gf         | 257.625 |       257.625 |
| ga         | 257.625 |       257.625 |
| net_rating |     0.0 |           0.0 |

**Gate:** league mean net after shrink is `≈0` (observed exact `0.0`). Closed league ΣGF = ΣGA — not a second knob. Not recentered.

---

## 32-team table (pre → post)

|  Rk | Team | W-L-OTL (Pts)  | GF pre→post | GA pre→post | Net pre→post |
| --: | ---- | -------------- | ----------- | ----------- | ------------ |
|   1 | COL  | 55-16-11 (121) | 302→295.16  | 203→211.01  | +99→+84.15   |
|   2 | TBL  | 50-26-6 (106)  | 290→284.96  | 231→234.81  | +59→+50.15   |
|   3 | CAR  | 53-22-7 (113)  | 296→290.06  | 240→242.46  | +56→+47.60   |
|   4 | DAL  | 50-20-12 (112) | 279→275.61  | 226→230.56  | +53→+45.05   |
|   5 | BUF  | 50-23-9 (109)  | 288→283.26  | 241→243.31  | +47→+39.95   |
|   6 | MIN  | 46-24-12 (104) | 272→269.66  | 240→242.46  | +32→+27.20   |
|   7 | OTT  | 44-27-11 (99)  | 278→274.76  | 246→247.56  | +32→+27.20   |
|   8 | UTA  | 43-33-6 (92)   | 268→266.26  | 240→242.46  | +28→+23.80   |
|   9 | MTL  | 48-24-10 (106) | 283→279.01  | 256→256.06  | +27→+22.95   |
|  10 | PIT  | 41-25-16 (98)  | 293→287.51  | 268→266.26  | +25→+21.25   |
|  11 | BOS  | 45-27-10 (100) | 272→269.66  | 250→250.96  | +22→+18.70   |
|  12 | WSH  | 43-30-9 (95)   | 263→262.01  | 244→245.86  | +19→+16.15   |
|  13 | VGK  | 39-26-17 (95)  | 265→263.71  | 250→250.96  | +15→+12.75   |
|  14 | EDM  | 41-30-11 (93)  | 282→278.16  | 269→267.11  | +13→+11.05   |
|  15 | PHI  | 43-27-12 (98)  | 250→250.96  | 243→245.01  | +7→+5.95     |
|  16 | CBJ  | 40-30-12 (92)  | 253→253.51  | 253→253.51  | +0→+0.00     |
|  17 | NYI  | 43-34-5 (91)   | 233→236.51  | 241→243.31  | −8→−6.80     |
|  18 | NYR  | 34-39-9 (77)   | 238→240.76  | 250→250.96  | −12→−10.20   |
|  19 | ANA  | 43-33-6 (92)   | 273→270.51  | 288→283.26  | −15→−12.75   |
|  20 | DET  | 41-31-10 (92)  | 241→243.31  | 258→257.76  | −17→−14.45   |
|  21 | LAK  | 35-27-20 (90)  | 225→229.71  | 247→248.41  | −22→−18.70   |
|  22 | NSH  | 38-34-10 (86)  | 247→248.41  | 269→267.11  | −22→−18.70   |
|  23 | NJD  | 42-37-3 (87)   | 230→233.96  | 254→254.36  | −24→−20.40   |
|  24 | FLA  | 40-38-4 (84)   | 251→251.81  | 276→273.06  | −25→−21.25   |
|  25 | STL  | 37-33-12 (86)  | 231→234.81  | 258→257.76  | −27→−22.95   |
|  26 | WPG  | 35-35-12 (82)  | 231→234.81  | 260→259.46  | −29→−24.65   |
|  27 | SEA  | 34-37-11 (79)  | 226→230.56  | 263→262.01  | −37→−31.45   |
|  28 | SJS  | 39-35-8 (86)   | 251→251.81  | 292→286.66  | −41→−34.85   |
|  29 | TOR  | 32-36-14 (78)  | 253→253.51  | 299→292.61  | −46→−39.10   |
|  30 | CGY  | 34-39-9 (77)   | 212→218.66  | 259→258.61  | −47→−39.95   |
|  31 | CHI  | 29-39-14 (72)  | 213→219.51  | 275→272.21  | −62→−52.70   |
|  32 | VAN  | 25-49-8 (58)   | 216→222.06  | 316→307.06  | −100→−85.00  |

---

## Gates

| Gate                                        | Result                                   |
| ------------------------------------------- | ---------------------------------------- |
| 32 rows                                     | **PASS**                                 |
| Mean net ≈ 0                                | **PASS** (exact `0.0`)                   |
| No top/bottom invert / no lottery favorites | **PASS** (COL…BUF top; SEA…VAN bottom)   |
| KEINHL still blank                          | **PASS** (`sportIsMarketsOnlyEdgeBoard`) |
| NBA / WNBA shrink constants untouched       | **PASS**                                 |
| CFB BALL@OSU still −40.5                    | **PASS** (`kei_spread_home=-40.51`)      |
| No Edge tags / xG / player tables           | **PASS**                                 |

**Stop.** Chapter 2 is TOI grid + goalie tandem (`docs/NHL_CH2_TOI_GRID_BRIEF.md`). Not emit.
