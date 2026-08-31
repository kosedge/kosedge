# CFB Chapter 2 Phase 1E — low-sample QB talent

**Stamp:** `cfb-season-engine-v0.15-power-sot` + 1C soft ceiling (τ=0.16) + 1D `min(22,att/22)`  
**Brief:** `docs/CFB_CH2_QB_LOWSAMPLE_BRIEF.md`  
**Lever:** `resolve_qb_talent` in `scripts/cfb/package_real_roster_2026.py` only (1D formula untouched)

## Phase 0 — `talent_from_qb_stats` after 1D (quoted)

```357:374:scripts/cfb/package_real_roster_2026.py
def talent_from_qb_stats(attempts: int, yards: int, tds: int, *, is_portal: bool) -> float:
    ...
    base = (
        42.0
        + min(22.0, attempts / 22.0)
        + min(12.0, ypa * 1.1)
        + min(10.0, tds * 0.35)
    )
```

Three throws (STAN/BALL) still land ~50 under that formula — volume missing, not a measured mid grade.

## Phase 0 — attempts histogram (power-board n=125)

| pct | attempts |
| --- | -------: |
| p10 |       19 |
| p25 |       82 |
| p50 |      262 |
| p75 |      362 |
| p90 |      413 |

**N = 80.** `att < 80` → **31** power-board QBs.  
**MICH (82 att) is OUT** of treatment — stays on the pure 1D stats path.

## Phase 0 — fallback field (not a blocker)

| Field                               | Location                                                                                                                    |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **`roster.recruiting_class_score`** | Packaged ~`package_real_roster_2026.py:656–657` / written `:775–776`; mirrors `recruiting_capital`; CFBD overlay `:912–913` |

STAN recruit **70** vs stats talent **~50.55**; BALL recruit **55** vs **~49.27**. Fallback is **not** “league 50 only” → chapter is a **fit**, not a blocker.

## Phase 0 — full list `att < 80` (power board; stats talent = pre-1E)

| team | att | talent now (1D stats) | qb_class         | starter                |
| ---- | --: | --------------------: | ---------------- | ---------------------- |
| BC   |   0 |                 52.0† | open_competition | Enzo Arjona            |
| BUFF |   0 |                  48.0 | open_competition | Elijah Holmes          |
| TEM  |   0 |                  48.0 | open_competition | Ajani Sheppard         |
| NAVY |   2 |                 42.09 | open_competition | Jackson Gutierrez      |
| BALL |   3 |             **49.27** | open_competition | Keldric Luster         |
| MEM  |   3 |                  46.9 | open_competition | Air Noland             |
| STAN |   3 |             **50.55** | open_competition | Charlie Mirer          |
| HOU  |   7 |                 45.78 | true_freshman    | Luke Carney            |
| JMU  |  10 |                 48.94 | open_competition | Arrington Maiden       |
| RICE |  15 |                 48.39 | true_freshman    | Patrick Crayton Jr.    |
| UNC  |  16 |                  52.5 | open_competition | Billy Edwards Jr.      |
| FRES |  17 |                 49.92 | open_competition | Khristian Martin       |
| VAN  |  17 |                  53.6 | open_competition | Blaze Berlowitz        |
| FAU  |  21 |                 49.75 | incumbent        | Drew Devillier         |
| IOWA |  21 |                 50.91 | open_competition | Hank Brown             |
| TULN |  21 |                 50.96 | open_competition | Zeon Chriss-Gremillion |
| GT   |  24 |                 56.84 | incumbent        | Alberto Mendoza        |
| UK   |  26 |                 51.47 | incumbent        | Kenny Minchey          |
| UGA  |  27 |                 50.14 | incumbent        | Ryan Puglisi           |
| AFA  |  28 |                 56.67 | incumbent        | Josh Johnson           |
| CMU  |  28 |                 53.63 | open_competition | Angel Flores           |
| ALA  |  32 |                 51.99 | incumbent        | Austin Mack            |
| UF   |  35 |                 50.29 | true_freshman    | Tramell Jones Jr.      |
| APP  |  39 |                 48.71 | true_freshman    | Noah Gillon            |
| CCU  |  47 |                 52.68 | true_freshman    | Deuce Bailey           |
| CONN |  52 |                 54.45 | true_freshman    | Kalieb Osborne         |
| USM  |  52 |                 55.65 | portal           | Landry Lyddy           |
| ARK  |  54 |                 54.49 | incumbent        | KJ Jackson             |
| TENN |  55 |                 54.09 | incumbent        | Ryan Staub             |
| BGSU |  66 |                 54.63 | incumbent        | Hunter Najm            |
| CLEM |  71 |                 52.92 | incumbent        | Christopher Vizzina    |

† portal floor when `attempts<=0` inside `talent_from_qb_stats`.

## Phase 1 — change

```text
N = 80
stats = talent_from_qb_stats(...)          # 1D unchanged
if att >= N: talent = stats
else:
  w = sqrt(att / N)                        # w(0)=0, w(N)=1
  talent = (1-w)*recruiting_class_score + w*stats
```

Linear `att/N` over-lifted blue-blood thin samples and **reordered top-7**; **`sqrt`** tightens the pull (brief: tighten blend, do not add `if P4`).

Rematerialized `qb_talent` in:

- `cfb_fbs_team_priors_2026.json`
- `cfb_real_roster_snapshot_2026.json`

KEI W0/W1 regenerated from new means (futures **not** rewritten).

## After (key teams)

| team | att |                   talent | published qb_index |
| ---- | --: | -----------------------: | -----------------: |
| OSU  | 391 |    **79.93** (unchanged) |         **1.3808** |
| HAW  | 430 |    **77.89** (unchanged) |         **1.3625** |
| TCU  | 338 |    **75.45** (unchanged) |         **1.3594** |
| STAN |   3 | **66.23** (↑ from 50.55) |         **1.0743** |
| BALL |   3 | **53.89** (↑ from 49.27) |         **0.9174** |
| MICH |  82 |   **52.62** (stats path) |                  — |

**OSU > HAW > TCU** still.

## Canaries

| Gate                       | Result                                                                    |
| -------------------------- | ------------------------------------------------------------------------- |
| Top-7 power order          | **FLAT** OSU, ORE, MISS, MIA, IU, TAMU, ND                                |
| OSU qb_index > HAW > TCU   | PASS                                                                      |
| HAW talent unchanged       | **77.89** PASS                                                            |
| STAN talent up from ~50.58 | **66.23** PASS (recruit fallback real)                                    |
| BALL@OSU cupcake           | model **−40.85** · KEI **−42.05** · WP **0.98** PASS                      |
| TCU margin                 | **16.48** (not required to hold 18.73; volume ≥ N) reported               |
| HAW@STAN raw/KEI           | model **+6.62** · KEI **+7.62** (still wrong side; flip **not** required) |
| USF vs OSU E[wins]         | futures not cloned / not rewritten                                        |
| Utah                       | **6.2%** PASS                                                             |

## Forbidden check

No `if team == Stanford/Hawaii/Ball State`. No 1C τ edit. No 1D divisor edit. No `WEIGHT_QB` / `MATCHUP_RESPONSE`. No invented recruiting. No power_sot rematerialize. No Utah / NFL/CBB/MLB trees.
