# WNBA Chapter 1 — team prior scorecard

**Stamp:** `wnba-season-engine-v0.1` · `as_of=2026-09-01` · season `2026` YTD (midseason)  
**Chosen:** `WNBA_TEAM_CARRY_SHRINK = 0.85`  
**Brief:** [`docs/WNBA_CH1_TEAM_PRIOR_BRIEF.md`](./WNBA_CH1_TEAM_PRIOR_BRIEF.md)  
**Pack:** `services/model-service/src/services/wnba_season_engine/data/wnba_team_prior_2026.json`

---

## Paper-sim (`s` set)

|                 s | mean net post | net σ pre→post | MIN net′ | CON net′ | lottery in top-5 |
| ----------------: | ------------: | -------------- | -------: | -------: | ---------------- |
|              0.70 |          0.04 | 6.8094→4.7666  |    7.012 |   -7.688 | none             |
|              0.80 |          0.04 | 6.8094→5.4475  |    8.008 |   -8.792 | none             |
| 0.85 **← chosen** |          0.04 | 6.8094→5.7880  |    8.506 |   -9.344 | none             |
|              0.90 |          0.04 | 6.8094→6.1284  |    9.004 |   -9.896 | none             |

Affine shrink with `s∈(0,1]` preserves rank order. No lottery club (worst-5 by wins: CHI / PHX / SEA / TOR / CON) enters the post-shrink top-5 at any candidate `s`.

**Pick rationale:** 0.85 — order-preserving, modest compression of near-complete YTD (~40 GP). Own name `WNBA_TEAM_CARRY_SHRINK` (not NBA’s constant).

---

## League means

| Metric     |        Pre | Post (s=0.85) |
| ---------- | ---------: | ------------: |
| ortg       | 109.286667 |    109.286667 |
| drtg       | 109.246667 |    109.246667 |
| net_rating |       0.04 |          0.04 |
| pace       |  79.253333 |     79.253333 |

**Gate:** league mean net after shrink is `≈0` (observed `0.04`). Micro-offset is BR / rounding across 15 teams — not a second knob. Not recentered.

---

## 15-team table (pre → post)

|  Rk | Team | W-L   | ORtg pre→post | DRtg pre→post | Net pre→post | Pace pre→post |
| --: | ---- | ----- | ------------- | ------------- | ------------ | ------------- |
|   1 | MIN  | 31-9  | 115.4→114.48  | 105.4→105.98  | +10.0→+8.51  | 79.2→79.21    |
|   2 | GSV  | 29-11 | 110.9→110.66  | 101.3→102.49  | +9.6→+8.17   | 74.5→75.21    |
|   3 | IND  | 26-14 | 117.9→116.61  | 110.5→110.31  | +7.4→+6.30   | 81.2→80.91    |
|   4 | ATL  | 26-14 | 112.3→111.85  | 106.0→106.49  | +6.3→+5.36   | 80.6→80.40    |
|   5 | LAS  | 27-13 | 113.4→112.78  | 108.3→108.44  | +5.1→+4.34   | 79.4→79.38    |
|   6 | DAL  | 24-16 | 113.0→112.44  | 108.3→108.44  | +4.7→+4.00   | 78.3→78.44    |
|   7 | NY   | 24-16 | 113.1→112.53  | 109.4→109.38  | +3.7→+3.15   | 78.9→78.95    |
|   8 | WSH  | 24-16 | 105.3→105.90  | 105.6→106.15  | −0.3→−0.25   | 77.2→77.51    |
|   9 | CHI  | 15-25 | 105.5→106.07  | 109.1→109.12  | −3.6→−3.05   | 81.7→81.33    |
|  10 | PHX  | 14-26 | 106.3→106.75  | 110.2→110.06  | −3.9→−3.31   | 79.0→79.04    |
|  11 | LA   | 15-25 | 106.9→107.26  | 112.4→111.93  | −5.5→−4.67   | 81.4→81.08    |
|  12 | POR  | 16-24 | 108.9→108.96  | 114.6→113.80  | −5.7→−4.84   | 78.5→78.61    |
|  13 | SEA  | 8-32  | 102.8→103.77  | 109.5→109.46  | −6.7→−5.69   | 80.3→80.14    |
|  14 | TOR  | 11-29 | 108.2→108.36  | 117.7→116.43  | −9.5→−8.07   | 79.4→79.38    |
|  15 | CON  | 10-30 | 99.4→100.88   | 110.4→110.23  | −11.0→−9.34  | 79.2→79.21    |

TOR / POR flagged `expansion_ytd_only` — YTD + shrink only; no invented 2025 row.

---

## Gates

| Gate                                        | Result                                                        |
| ------------------------------------------- | ------------------------------------------------------------- |
| Every 2026 team has a row (15)              | **PASS**                                                      |
| Mean net ≈ 0                                | **PASS** (offset `0.04` documented)                           |
| No top/bottom invert / no lottery favorites | **PASS** (MIN…LAS top; LA…CON bottom)                         |
| Live CON@ATL market untouched               | **PASS** (no board/Odds write; leftover KEI still Aug-1 only) |
| NBA HOU/OKC KEI still ≈ +4.2 / −4.2         | **PASS** (`0022500001` `kei_spread_home=-4.16`)               |
| CFB BALL@OSU still −40.5                    | **PASS** (`kei_spread_home=-40.51`)                           |
| No Edge tags / props / KEI emit             | **PASS**                                                      |
| Aug-1 leftovers not blended                 | **PASS** (`forbidden_leftover_fair_line_game_ids`)            |

Board leftover (LAS @ CHI +4.5 / NY @ PHX +2.5 from `401857105`/`401857106`) remains leftover.  
**Stop.** Chapter 2 is next.
