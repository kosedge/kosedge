# CFB Chapter 2 Phase 1A — compose / eff / QB inputs (DISCOVERY ONLY)

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Brief:** `docs/CFB_CH2_COMPOSE_QB_BRIEF.md`  
**Phase 0 locked:** TCU raw +19.19 (still ~13.7 @ RESPONSE=1.00); HAW@STAN −9.9 (−6.4 @ 1.00).  
**This PR:** **no** writes to compose weights, `MATCHUP_RESPONSE`, power sort, SD, or KEI.

Compose spine (`team_projection.py:85–161`):

```text
offense_score = 0.34*off_eff + 0.22*roster + 0.24*qb_score + 0.10*skill + 0.10*ol
offense_index = score_to_index(score)
offense_index = (1-0.26)*idx + 0.26*(idx*qb_index)     # QB_INDEX_BLEND
+ OL/skill blends + EFF_OFF_INDEX_BLEND(0.12) + coaching mult
```

Weights: `priors.py:183–212`.

---

## Four-team input table (required)

| Term                       |         UNC |            TCU |            HAW |        STAN | File:line                     |
| -------------------------- | ----------: | -------------: | -------------: | ----------: | ----------------------------- |
| off_eff                    |   **24.92** |      **64.74** |          50.21 |   **28.18** | efficiency pack → compose     |
| def_eff                    |       53.13 |          56.29 |          47.78 |       44.37 |                               |
| qb_situation_score         |       43.62 |       **80.4** |       **80.4** |       41.97 | `qb_situation`                |
| qb_situation_index         |      0.9203 | **1.38** (cap) | **1.38** (cap) |      0.8996 | `QB_SITUATION_INDEX_CLAMP`    |
| roster_strength            |       62.20 |          62.44 |          55.64 |       60.88 |                               |
| returning_production       |       55.58 |          60.82 |          60.91 |       59.77 | `roster.returning_production` |
| returning_snap_share       |       0.556 |          0.608 |          0.609 |       0.598 |                               |
| OL / skill                 | 59.8 / 62.1 |    61.8 / 62.3 |    54.0 / 55.5 | 63.2 / 60.8 |                               |
| coaching O/D mult          |   1.0 / 1.0 |      1.0 / 1.0 |      1.0 / 1.0 |   1.0 / 1.0 | returning staff               |
| **offense_score** (0–100)  |       44.81 |      **67.45** |          59.56 |       45.44 | `team_projection.py:107–113`  |
| score Δ vs all-50 (eff)    |   **−8.53** |          +5.01 |          +0.07 |   **−7.42** |                               |
| score Δ vs all-50 (QB)     |       −1.53 |      **+7.30** |      **+7.30** |       −1.93 |                               |
| score Δ vs all-50 (roster) |       +2.68 |          +2.74 |          +1.24 |       +2.39 |                               |
| idx after score→index      |       0.924 |          1.257 |          1.141 |       0.933 | `:123`                        |
| **Δ after QB_INDEX_BLEND** |      −0.019 |     **+0.124** |     **+0.113** |      −0.024 | `:125–128`                    |
| Δ after eff index blend    |      −0.041 |         +0.037 |             ~0 |      −0.036 | `:140–142`                    |
| **offense_index**          |  **0.8866** |     **1.4571** |     **1.2675** |  **0.8987** | live                          |
| defense_index              |      1.1375 |         1.1782 |         1.0599 |      1.0667 |                               |
| power 0.5\*(O+D)           |       1.012 |          1.318 |          1.164 |       0.983 | `power_sot.py:128`            |

### Offense_score parts (points of 0–100 score, not game pts)

| Part     |   UNC |       TCU |       HAW |  STAN | Weight |
| -------- | ----: | --------: | --------: | ----: | -----: |
| eff      |  8.47 | **22.01** |     17.07 |  9.58 |   0.34 |
| roster   | 13.68 |     13.74 |     12.24 | 13.39 |   0.22 |
| qb_score | 10.47 | **19.30** | **19.30** | 10.07 |   0.24 |
| skill+ol | 12.19 |     12.41 |     10.95 | 12.40 |   0.20 |

---

## Share of TCU **36.67** and HAW **31.81** (points)

Leave-one-out: recompose with that input at league avg (eff/roster/qb_score=50, qb_index=1.0, units=50), keep opponent fixed, re-run `expected_team_points` + ST (week 0). **Attributable = live − avg-ablated.**

### TCU home expected 36.67 (vs UNC, Dublin)

| Lever set to avg              | TCU pts | Attributable to live prior |
| ----------------------------- | ------: | -------------------------: |
| **QB score+index → 50 / 1.0** |   28.43 |                  **+8.24** |
| OL+skill → 50                 |   32.32 |                      +4.35 |
| off_eff → 50                  |   32.54 |                      +4.13 |
| roster → 50                   |   35.05 |                      +1.62 |
| coaching (already 1.0)        |       — |                      **0** |

UNC away 17.48: largest own term is **weak off_eff** (setting eff→50 raises UNC to 22.19, i.e. live eff costs UNC **−4.71**). That matches the board result (UNC scored **15**) — UNC prior is not the miss; **TCU 36.67 vs actual 10** is.

### Hawaiʻi away expected 31.81 (vs STAN)

| Lever set to avg              | HAW pts |      Attributable |
| ----------------------------- | ------: | ----------------: |
| **QB score+index → 50 / 1.0** |   24.33 |         **+7.48** |
| OL+skill → 50                 |   30.17 |             +1.64 |
| roster → 50                   |   31.11 |             +0.70 |
| **off_eff → 50**              |   31.76 | **+0.05** (~none) |

Hawaii’s road explosion is **QB prior (80.4 / 1.38)**, not SP+/eff (off_eff ≈ 50). Stanford’s low 21.91 is mostly **weak off_eff 28.18** (ablating to 50 raises STAN to 26.58).

---

## Why those scores (Phase 0 questions)

1. **TCU 36.67 / UNC 17.48:** Index gap from TCU high off_eff + capped QB vs UNC collapsed off_eff; then ratio^1.40. UNC scoring prior ≈ right (15 actual). TCU offense prior wildly high for that game.
2. **HAW 31.81 road / STAN 21.91 home:** Hawaii ≈ league-avg eff but **same QB cap as TCU**; Stanford bad off_eff; +1.7 HFA not enough.
3. **QB vs eff vs roster:** For TCU points, QB ≈ 8.2, eff ≈ 4.1, roster ≈ 1.6. For Hawaii points, QB ≈ 7.5, eff ≈ 0, roster ≈ 0.7.
4. **Named lever without inverting BALL@OSU:** see recommendation + paper sim.

---

## Paper sim ±10% (do not apply)

Both teams in each game scaled; week-0 expected points + ST. OSU path same.

| Lever    |     Scale | TCU margin | HAW@STAN home margin | OSU spread | Notes                                  |
| -------- | --------: | ---------: | -------------------: | ---------: | -------------------------------------- |
| baseline |       1.0 | **+19.19** |  **−9.90** (HAW fav) | **−45.31** |                                        |
| **QB**   |       0.9 |     +17.42 |                −8.52 |     −43.71 | Still wrong side; TCU only −1.8        |
| QB       |       1.1 |     +19.34 |                −9.87 |     −45.19 | Cap binds (TCU/HAW/OSU already @ 1.38) |
| **Eff**  |       0.9 |     +18.63 |                −9.52 |     −44.52 | Tiny; no flip                          |
| Eff      |       1.1 |     +19.71 |               −10.27 |     −45.33 | Slightly worse TCU                     |
| Roster   | 0.9 / 1.1 |      ~19.2 |                ~−9.9 |     ~−45.2 | Negligible                             |

**Top-7** if global ±10% on all packaged teams:

| Lever  | 0.9                                    | 1.1                                   |
| ------ | -------------------------------------- | ------------------------------------- |
| QB     | OSU **MISS** ORE … (**ORE/MISS swap**) | flat                                  |
| Eff    | OSU MISS ORE … + IU/TAMU shuffle       | OSU ORE **MIA IU MISS** … **CHANGED** |
| Roster | flat                                   | flat                                  |

No ±10% global scale reaches desk (−7.5 / STAN −4) without a much larger move that would hit OSU’s capped QB and/or shuffle top-7.

---

## Recommendation line (required)

**E — not A–C; file: `services/model-service/src/services/cfb_season_engine/qb_situation.py` (+ packaged QB situation priors that emit score 80.4 / index 1.38).**

| Option                                 | Verdict                                                                                                                                                                              |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A) QB prior **scale** (global)         | Largest term, but ±10% fails desk + shuffles top-7 at 0.9; upscale no-ops on cap                                                                                                     |
| B) Efficiency scale (global)           | Helps TCU–UNC gap some; **does not** explain Hawaii (eff≈50); shuffles top-7                                                                                                         |
| C) Roster/returning                    | ~1–2 pts; irrelevant                                                                                                                                                                 |
| D) Blocker / Ch3 only                  | Dublin already 0; HFA not Hawaii’s bug — too weak as sole next step                                                                                                                  |
| **E) QB situation input construction** | **Pick** — same 80.4/1.38 on TCU and HAW drives both exhibits; audit **how** class/talent maps to score/index (no team `if`), with top-7 + BALL@OSU canaries, before any weight edit |

**Do not** set `MATCHUP_RESPONSE=1.00` (still leaves TCU ~13.7 and HAW wrong-side ~−6.4; crushes cupcakes).

### Blocker if 1B tries A as a silent weight nudge

Global `WEIGHT_QB_SITUATION` / `QB_INDEX_BLEND` haircut large enough to mint TCU −8.5 will move OSU (also qb_index 1.38) and is rejected by the paper sim family.

---

## Forbidden check

No edits to `compose_team_projection`, `MATCHUP_RESPONSE`, `build_power_sot`, priors SD, `apply_cfb_kei` in this PR.
