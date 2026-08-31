# CFB Chapter 2 Phase 0 audit — raw margin / compose (DISCOVERY ONLY)

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Brief:** `docs/CFB_CH2_POWER_UNITS_BRIEF.md`  
**Method:** live `compose_team_projection` → `expected_team_points` → `project_game` → `apply_cfb_kei` (read-only).  
**This PR:** **zero** writes to compose weights, `MATCHUP_RESPONSE`, power sort, KEI, or SD.

Chapter 1 locked: TCU KEI **−20.39**; HAW@STAN **+10.9** wrong side. Short-bucket map **not** on this `deploy-vercel` tip (`BUCKET_MARGIN_SCALE` absent); for \|raw\|≥7 it would be identity anyway.

Spine file:line:

| Step               | File:line                                            |
| ------------------ | ---------------------------------------------------- |
| Compose            | `team_projection.py:85`                              |
| Expected points    | `team_projection.py:309–371`                         |
| HFA resolve        | `home_field.py:187–205`                              |
| ST + margin        | `team_projection.py:558–566`                         |
| Power `0.5*(O+D)`  | `power_sot.py:128–157`                               |
| `MATCHUP_RESPONSE` | `priors.py:107` (=1.40); week mapper `priors.py:310` |

---

## Mandatory team table (live)

| Term                           |       UNC |            TCU |            HAW |      STAN | File:line                                                                        |
| ------------------------------ | --------: | -------------: | -------------: | --------: | -------------------------------------------------------------------------------- |
| offense_index                  |    0.8866 |     **1.4571** |     **1.2675** |    0.8987 | `team_projection.py:85–161`                                                      |
| defense_index                  |    1.1375 |         1.1782 |         1.0599 |    1.0667 | same                                                                             |
| power 0.5\*(O+D)               |     1.012 |     **1.3176** |     **1.1637** |    0.9827 | `power_sot.py:128`                                                               |
| QB term (`qb_situation_index`) |    0.9203 | **1.38** (cap) | **1.38** (cap) |    0.8996 | compose + `priors.QB_INDEX_BLEND`                                                |
| roster_strength                |     62.20 |          62.44 |          55.64 |     60.88 | `roster.roster_strength`                                                         |
| returning_production           |     55.58 |          60.82 |          60.91 |     59.77 | `roster.returning_production`                                                    |
| returning_snap_share           |    0.5558 |         0.6082 |         0.6091 |    0.5977 | `roster.returning_snap_share` (feeds roster_strength; not a separate pts addend) |
| unit OL                        |     59.75 |          61.79 |          54.01 |     63.16 | `position_groups`                                                                |
| unit skill                     |     62.10 |          62.31 |          55.50 |     60.76 |                                                                                  |
| unit F7                        |     59.90 |          60.39 |          56.91 |     59.45 |                                                                                  |
| unit secondary                 |     60.87 |          63.34 |          56.73 |     59.30 |                                                                                  |
| unit ST grade                  |     66.43 |          65.74 |          55.39 |     63.63 |                                                                                  |
| offense_boost (from units)     |    1.0151 |         1.0168 |         1.0066 |    1.0169 | `team_projection.py:285–292`                                                     |
| coaching new_hc/oc/dc          |     F/F/F |          F/F/F |          F/F/F |     F/F/F | all returning                                                                    |
| coaching index mult O/D        | 1.0 / 1.0 |      1.0 / 1.0 |      1.0 / 1.0 | 1.0 / 1.0 |                                                                                  |
| off_eff (compose input)        | **24.92** |      **64.74** |      **50.21** | **28.18** | efficiency pack                                                                  |
| def_eff                        |     53.13 |          56.29 |          47.78 |     44.37 |                                                                                  |

---

## Mandatory game table

| Term                                |                                                        UNC@TCU |                                HAW@STAN | File:line                                                  |
| ----------------------------------- | -------------------------------------------------------------: | --------------------------------------: | ---------------------------------------------------------- |
| site flag                           |                                **neutral Dublin** (both sides) |                    STAN home / HAW away | slate `neutral_site`                                       |
| expected pts **before HFA** (home)  |                                                         36.553 |                                  20.141 | `pre_clamp − hfa` from `expected_team_points`              |
| expected pts **before HFA** (away)  |                                                         17.364 |                                  31.740 |                                                            |
| HFA applied? (home pts)             |                 **0.0** (`reason=neutral_site`, applied=false) | **+1.7** (`variable_hfa`, applied=true) | `home_field.py:195–205`                                    |
| HFA away                            |                                                            0.0 |                                     0.0 |                                                            |
| ST nudge (total, split 50/50)       |                                                         +0.241 |                                  +0.143 | `team_projection.py:561` `SPECIAL_TEAMS_TOTAL_SCALE=0.015` |
| home_exp (final)                    |                                                      **36.67** |                               **21.91** | `project_game`                                             |
| away_exp (final)                    |                                                      **17.48** |                               **31.81** |                                                            |
| raw margin home                     |                                                     **+19.19** |                               **−9.90** |                                                            |
| MATCHUP_RESPONSE                    |                                       1.40 (week 0, no soften) |                                    1.40 | `priors.py:310`                                            |
| margin @ response 1.40              |                                                         +19.19 |                                   −9.90 |                                                            |
| margin @ response 1.00              |                                                         +13.68 |                                   −6.43 | same ratios, core rescaled                                 |
| **1.40 contribution (pts vs 1.00)** |                                                      **+5.51** |                               **−3.47** | amplifies existing sign                                    |
| short-bucket map 1.188 applied?     | **no** (\|raw\|=19.19≥7; map absent on tip / identity on long) |                  **no** (\|raw\|=9.9≥7) | Ch1 map only scales **short** \|m\|∈[3,7)                  |
| model spread_home                   |                                                         −19.19 |                                   +9.90 |                                                            |
| KEI after bias guard                |                                                     **−20.39** |                              **+10.90** | `cfb_kei.py:250`                                           |
| desk close                          |                                                       **−7.5** |                                **−4.0** | Chapter 0 tape                                             |

**Dublin one-liner:** `project_game` does **not** add `HFA_BASELINE_POINTS=1.7` to TCU — `resolve_hfa_points` zeros HFA when `neutral_site` (`home_field.py:195`). Measured here; not a Chapter 3 leak.

---

## project_game terms for UNC@TCU (every addend)

Week **0**, **neutral**.

1. **Compose** builds TCU offense_index **1.457** vs UNC **0.887** — driven by off_eff **64.74 vs 24.92** and QB index **1.38 vs 0.9203**. Roster/units nearly tied.
2. **Matchup ratios:** TCU 1.281 · UNC 0.7525 (`team_projection.py:324`).
3. **Response 1.40** spends that gap (+5.51 pts vs linear).
4. **Units** ~+1.6% / dampen ~−2% — small.
5. **HFA = 0** (neutral).
6. **Coaching** +0.15 both (cancels in margin).
7. **ST** +0.24 total split.
8. **Scores 36.67–17.48 → raw +19.19 → KEI −20.39.**

Power gap TCU−UNC = **0.3056** (~2.7× OSU−ND **0.1152**).

---

## project_game terms for HAW@STAN (every addend)

Week **0**, Stanford home.

1. **Compose** has Hawaii ahead: offense_index **1.268 vs 0.899**, power **1.164 vs 0.983**, QB **1.38 vs 0.900**, off_eff **50.21 vs 28.18**.
2. Stanford units are _better_; still lose on eff+QB.
3. **HFA +1.7 applied** to Stanford — without it, wrong-side margin would be worse.
4. **Response 1.40** adds **−3.47** home margin (helps Hawaii).
5. **Scores 21.91–31.81 → raw −9.9 → KEI +10.9.** Polarity is compose, not HFA.

---

## What MATCHUP_RESPONSE=1.40 does to a mid-tier gap

`matchup = ratio ** response` (`team_projection.py:323–329`). Week 0 uses full **1.40** (early soften is W1–W4 only).

| Game     | Favorite ratio | @1.00 margin | @1.40 margin |     Δ pts |
| -------- | -------------: | -----------: | -----------: | --------: |
| UNC@TCU  |          1.281 |       +13.68 |   **+19.19** | **+5.51** |
| HAW@STAN |   1.188 (away) |        −6.43 |    **−9.90** | **−3.47** |

Response does not invent the sign. It **spends** an existing index gap into points.

---

## HFA_BASELINE 1.7 on Dublin neutral — is neutral applied?

**Yes.** `home_field.py:195–205`: `if neutral_site: hfa_points=0.0, reason=neutral_site`.  
Live UNC@TCU: `applied=false`, **0.0 pts**. Baseline 1.7 is **not** added to TCU.

---

## Power ticks: TCU vs UNC, STAN vs HAW vs OSU–ND 0.115

| Pair       | power_index gap |
| ---------- | --------------: |
| OSU − ND   |      **0.1152** |
| TCU − UNC  |      **0.3056** |
| HAW − STAN |      **0.1810** |
| OSU − BALL |      **0.7949** |

---

## Why cupcake raw margins can be "right" while TCU is long

Same response and unit scales. OSU−BALL gap **0.79** + elite HFA **+3.1** → model **−41** (short of a −50 book, right _direction_). TCU−UNC gap **0.31** + neutral 0 → model **−19** vs market **−7.5** (too much spend for a mid book). Crushing response to fix TCU would regress cupcakes — why Chapter 1 froze long/cupcake at 1.0.

---

## Phase 1 allowlist (units only vs compose weights — recommend one)

**Recommend: compose / efficiency–QB path — not units-only.**

| Option                                | Evidence                            | Verdict                                |
| ------------------------------------- | ----------------------------------- | -------------------------------------- |
| Units-only (`UNIT_*_SCALE` 0.07/0.09) | Live offense_boost ~1.01            | **Cannot** flip Hawaii or cut TCU 19→8 |
| Compose / eff+QB                      | Separators are off_eff + qb_index   | **Only** source-level lever            |
| Situation Ch3                         | Dublin already 0; STAN already +1.7 | Not the polarity fix                   |

If compose work is refused → **leave raw / research-only**, not a fake units ticket.

**Later allowlist (not this PR):** efficiency/QB input fidelity or named compose blends with **top-7 frozen**. Still no `if team`, no SD stretch, no Utah pass.

---

## Blocker conditions

| Condition                                      | Status                               |
| ---------------------------------------------- | ------------------------------------ |
| Units-only Phase 1 as TCU/Hawaii fix           | **Blocker**                          |
| Solo `MATCHUP_RESPONSE` crush to mint TCU −8.5 | **Blocker** (hurts cupcakes)         |
| Dublin HFA leak as TCU explanation             | **False** — neutral measured 0.0     |
| Hawaii flip via HFA hack                       | **Blocker** — HFA already helps STAN |
| Team-name branches / top-7 shuffle             | **Forbidden**                        |

**Phase 0 done.** Operator picks: compose/eff–QB fit vs research-only hold.
