# CFB Chapter 2 Phase 0 audit — raw margin / compose (DISCOVERY ONLY)

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Brief:** `docs/CFB_CH2_POWER_UNITS_BRIEF.md`  
**This PR:** zero writes to compose weights, `MATCHUP_RESPONSE`, power sort, KEI, or SD.

Chapter 1 locked: TCU KEI **−20.39** (raw margin **~19.19**); HAW@STAN KEI **+10.9** (wrong side). Short-bucket map 1.188 is **not** on `deploy-vercel` tip yet; this decomposition uses live `project_game` without that map (identity on long/cupcake/mid either way).

Spine (file:line):

| Step                | Location                                                                             |
| ------------------- | ------------------------------------------------------------------------------------ |
| Compose O/D indices | `team_projection.py:85` `compose_team_projection`                                    |
| Expected points     | `team_projection.py:309–371` `expected_team_points`                                  |
| HFA resolve         | `home_field.py:187–205` `resolve_hfa_points`                                         |
| ST nudge + margin   | `team_projection.py:558–566` `project_game`                                          |
| Matchup response    | `priors.py:107` `MATCHUP_RESPONSE=1.40`; `priors.py:310` `matchup_response_for_week` |

Formula (`team_projection.py:333–345`):

```text
pts = LEAGUE_TEAM_PPG(25.9) * (off/def)^response * off_boost * def_dampen * pace
    + HFA + coaching_week_adj
```

---

## project_game terms for UNC@TCU (every addend)

**Context:** Week **0**, **neutral** (Dublin). Slate home=TCU, away=UNC.

### Identity / power

| Side            | offense_index | defense_index | power_index | power rank |
| --------------- | ------------: | ------------: | ----------: | ---------: |
| TCU             |    **1.4571** |        1.1782 |  **1.3176** |         28 |
| UNC             |    **0.8866** |        1.1375 |   **1.012** |         99 |
| Gap (home−away) |               |               | **+0.3056** |            |

OSU−ND reference gap = **0.1152**. TCU−UNC is **~2.7×** that tick — already a large separation before matchup power.

### Compose inputs (dominant)

| Term                  |            TCU |           UNC | Notes                                              |
| --------------------- | -------------: | ------------: | -------------------------------------------------- |
| off_eff (0–100)       |      **64.74** |     **24.92** | `WEIGHT_OFF_EFF=0.34`                              |
| def_eff               |          56.29 |         53.13 | Similar                                            |
| qb_situation_index    | **1.38** (cap) |    **0.9203** | `WEIGHT_QB_SITUATION=0.24` + `QB_INDEX_BLEND=0.26` |
| roster_strength       |          62.44 |         62.20 | Nearly tied                                        |
| OL / skill / F7 / sec |         ~60–63 |        ~60–62 | Unit grades **not** the separator                  |
| Coaching flags        |  all returning | all returning | placeholder +0.15 both sides                       |

### `expected_team_points` addends (week 0 → response **1.40**)

| Addend                  |                      TCU (home) | UNC (away) |
| ----------------------- | ------------------------------: | ---------: |
| matchup_ratio (off/def) |                       **1.281** | **0.7525** |
| matchup_response        |                        **1.40** |   **1.40** |
| offense_boost (units)   |                          1.0168 |     1.0151 |
| defense_dampen (units)  |                          0.9814 |     0.9789 |
| pace                    |                          0.9959 |     0.9959 |
| **HFA**                 | **0.0** (`reason=neutral_site`) |    **0.0** |
| coaching_net_adj        |                           +0.15 |      +0.15 |
| pre_clamp / points      |                       **36.55** |  **17.36** |
| ST nudge (split)        |                           +0.12 |      +0.12 |
| **Final scores**        |                       **36.67** |  **17.48** |

| Derived           |      Value |
| ----------------- | ---------: |
| raw_margin_home   | **+19.19** |
| model spread_home | **−19.19** |
| KEI (bias guard)  | **−20.39** |

**Counterfactual:** if Dublin were _not_ neutral, TCU home would get ~+1.7 HFA → home pts **38.25** (even longer). Neutral is applied correctly and **shrinks** the home side vs a true home game.

**Response sensitivity (core scoring without HFA/coach):** at response 1.40 vs 1.0, TCU core **+3.43**, UNC core **−2.07** → ~**5.5 pts** of the 19-pt margin is `MATCHUP_RESPONSE` amplifying an already large off/def ratio. Units contribute ~±2% multipliers — not the story.

---

## project_game terms for HAW@STAN (every addend)

**Context:** Week **0**, Stanford home (not neutral).

### Identity / power

| Side            | offense_index | defense_index | power_index | power rank |
| --------------- | ------------: | ------------: | ----------: | ---------: |
| STAN (home)     |    **0.8987** |        1.0667 |  **0.9827** |        118 |
| HAW (away)      |    **1.2675** |        1.0599 |  **1.1637** |         62 |
| Gap (home−away) |               |               |  **−0.181** |            |

Model believes **Hawaii is the better team** before the kickoff. Market STAN −4 is the opposite polarity.

### Compose inputs (dominant)

| Term               |       STAN |            HAW | Notes                                        |
| ------------------ | ---------: | -------------: | -------------------------------------------- |
| off_eff            |  **28.18** |      **50.21** | Primary offense separator                    |
| def_eff            |      44.37 |          47.78 | Mild                                         |
| qb_situation_index | **0.8996** | **1.38** (cap) | Same QB-cap pattern as TCU                   |
| roster_strength    |      60.88 |          55.64 | Stanford slightly higher — **not** enough    |
| Units              |     ~59–63 |         ~54–57 | Stanford units better; still loses on eff+QB |
| Coaching           |  returning |      returning | +0.15 both                                   |

### `expected_team_points` addends

| Addend           |                        STAN (home) |          HAW (away) |
| ---------------- | ---------------------------------: | ------------------: |
| matchup_ratio    |                         **0.8479** |          **1.1882** |
| matchup_response |                           **1.40** |            **1.40** |
| offense_boost    |                             1.0169 |              1.0066 |
| defense_dampen   |                             0.9877 |              0.9831 |
| pace             |                             0.9682 |              0.9682 |
| **HFA**          | **+1.7** (applied, average bucket) | **0.0** (away_side) |
| coaching_net     |                              +0.15 |               +0.15 |
| points           |                          **21.84** |           **31.74** |
| ST nudge         |                              +0.07 |               +0.07 |
| **Final scores** |                          **21.91** |           **31.81** |

| Derived           |               Value |
| ----------------- | ------------------: |
| raw_margin_home   |            **−9.9** |
| model spread_home | **+9.9** (home dog) |
| KEI               |           **+10.9** |

**HFA is not the bug.** Stanford already receives +1.7. Removing it would make the wrong-side margin **worse**. Polarity is **compose identity** (eff + QB → offense_index → ratio), then `MATCHUP_RESPONSE=1.40` widens it (~3.5 pts vs response 1.0).

---

## What MATCHUP_RESPONSE=1.40 does to a mid-tier gap

`matchup = ratio ** response` (`team_projection.py:323–329`).

Week 0: `matchup_response_for_week(0) = 1.40` (no early soften; soften only W1–W4) — `priors.py:310–311`, `EARLY_SEASON_SEPARATION_SOFTEN`.

| Game            | Favorite ratio | ratio^1.0 | ratio^1.40 | Mult vs linear |
| --------------- | -------------: | --------: | ---------: | -------------: |
| TCU vs UNC def  |          1.281 |     1.281 |  **1.366** |      **+6.7%** |
| UNC vs TCU def  |         0.7525 |    0.7525 |  **0.699** |      **−7.1%** |
| HAW vs STAN def |          1.188 |     1.188 |  **1.243** |      **+4.6%** |
| STAN vs HAW def |          0.848 |     0.848 |  **0.812** |      **−4.2%** |

On a **mid-tier** gap like TCU−UNC (power 0.31), response 1.40 turns a large ratio into a **~19-pt** expected margin. It does not invent the sign — it **spends** an existing index gap into points. Cupcakes (BALL@OSU ratio raw 1.84 → clamped 1.61) get even more spend, which is why OSU can print −41 while TCU prints −19 on a smaller-but-still-large gap.

---

## HFA_BASELINE 1.7 on Dublin neutral — is neutral applied?

**Yes.** `resolve_hfa_points` (`home_field.py:195–205`):

```text
if neutral_site or not home:
    hfa_points = 0.0
    reason = "neutral_site" | "away_side"
```

UNC@TCU live diag: `applied=False`, `reason=neutral_site`, `hfa_points=0.0`.  
Baseline 1.7 is recorded but **not added**. Dublin is not leaking home HFA into the margin. Situation-layer (Chapter 3) is not the TCU lever for the 19-pt raw print.

---

## Power ticks: TCU vs UNC, STAN vs HAW vs OSU–ND 0.115

| Pair       | power_index gap | Notes                                 |
| ---------- | --------------: | ------------------------------------- |
| OSU − ND   |      **0.1152** | Top-7 adjacent tick (canary scale)    |
| TCU − UNC  |      **0.3056** | ~2.7× OSU−ND                          |
| HAW − STAN |      **0.1810** | Hawaii ahead; Stanford home still dog |
| OSU − BALL |      **0.7949** | Cupcake class                         |

Power sort key remains `0.5*(off+def)` (`power_sot.py:128–157`). These gaps are **outputs of compose**, not a separate ratings sheet. Rescaling power ticks without changing compose would fight the same indices `expected_team_points` already uses.

---

## Why cupcake raw margins can be "right" while TCU is long

|                      | BALL@OSU                         | UNC@TCU                                           |
| -------------------- | -------------------------------- | ------------------------------------------------- |
| Power gap            | 0.79                             | 0.31                                              |
| Ratio                | clamped ~1.61                    | 1.28 (unclamped)                                  |
| HFA                  | elite **+3.1**                   | neutral **0**                                     |
| Model spread         | **−41.0**                        | **−19.19**                                        |
| Market / close class | ~−50 (short of book)             | ~−7.5 (**long** vs book)                          |
| Failure mode         | Magnitude shy on a true mismatch | Magnitude / separation too large for a mid market |

Same `MATCHUP_RESPONSE` and unit scales. Cupcake is "right direction, maybe short of a −50 book." TCU is "wrong magnitude for a −7.5 book" because **compose built a 0.31 power gap and 1.28 ratio** (eff 65 vs 25, QB cap vs 0.92) that the curve honestly spends into ~19 points. Fixing TCU by crushing cupcake response would regress OSU WP/spread. That is why Chapter 1 froze long/cupcake scales at 1.0.

---

## Phase 1 allowlist (units only vs compose weights — recommend one)

**Recommend: compose / efficiency–QB path — not units-only.**

| Option                                                         | Evidence from this audit                               | Verdict                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------- |
| **Units-only** (`UNIT_OFFENSE_BOOST_SCALE` 0.07 / dampen 0.09) | Live boosts ~1.01–1.02; ST negligible                  | **Will not** flip Hawaii or cut TCU 19→8. Reject as sole Phase 1     |
| **Compose weights / eff+QB blends**                            | TCU/UNC and HAW/STAN separators are off_eff + qb_index | **Only lever** that changes sign/magnitude at the source             |
| Situation Ch3 (HFA/neutral)                                    | Dublin already neutral; STAN already +1.7              | Not the polarity fix; optional later for Dublin _information_ on KEI |

**Allowlist for a later Phase 1 PR (not this one):**

1. Discovery-gated edits to efficiency prior fidelity / QB situation inputs (or named compose blends) with **top-7 power order frozen**
2. Scorecard: TCU raw margin ↓ toward mid-band **without** OSU cupcake WP leaving the 90s; HAW@STAN side report (flip still not required if blocker)
3. Still forbidden: `if team ==`, stretching `WIN_PROB_MARGIN_SD`, Utah beauty pass, `MATCHUP_RESPONSE` solo crush as a TCU patch

If operator refuses compose-weight work, the honest alternative is **leave raw / research-only** on these two games until roster-efficiency SoT improves — not a fake units ticket.

---

## Blocker conditions

| Condition                                      | Status                                                           |
| ---------------------------------------------- | ---------------------------------------------------------------- |
| Units-only Phase 1 claimed to fix TCU/Hawaii   | **Blocker** — units are <2% of pts here                          |
| `MATCHUP_RESPONSE` solo crush to mint TCU −8.5 | **Blocker** — harms cupcake class; sign not invented by response |
| Dublin HFA "bug" as TCU explanation            | **False** — neutral applied (`home_field.py:195`)                |
| Hawaii flip via HFA hack                       | **Blocker** — HFA already helps Stanford                         |
| Team-name branches                             | **Forbidden**                                                    |
| Top-7 shuffle to make TCU look better          | **Forbidden**                                                    |

**Phase 0 done.** Operator picks next fit PR: compose/eff–QB (recommended) vs research-only hold. Not units-only.
