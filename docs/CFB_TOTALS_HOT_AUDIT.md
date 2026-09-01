# CFB totals hot vs market — audit (read-only)

**Date:** 2026-09-01  
**Scope:** Why live CFB Edge Board Week 1 Tag O/U is Over-drunk vs street.  
**Stamps:** pack `cfb-kei-v1.0-2026w0` · engine `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Evidence packs:** `apps/web/lib/data/cfb-kei-w0-w1-2026.json`, `data/ops/cfb-w1-handicap-card-20260831.json`  
**Not done:** no KEI recut, no haircut, no retune, no Edge Board / tagger code change, no merge.

---

## Verdict

The board is Over-drunk because **published KEI total is an uncalibrated identity copy of the research model total**, and Tag O/U fires on `|KEI − market|` with **no `|12|` absurd gate**. Spreads get a bias guard + trusted-market PASS; totals get neither.

This is **expected product shape**, not a double-count / sign / units bug. The +8 mean gap is mostly **matchup-response score inflation on real 2026 roster/QB identity** (asymmetric O/D ratios → both sides still score), not pace/explosiveness and not power-SoT fill.

---

## 1. How KEI total is computed (engine → pack → tag)

### Engine

`project_game` builds team expected points, then:

```text
total = home_exp + away_exp
spread_home = away_exp - home_exp
```

Formula (`team_projection.py`):

```text
pts = LEAGUE_TEAM_PPG * (off/def)^response * ol_skill_boost * opp_def_dampen * pace
    + variable_HFA + coaching_adj
(+ thin ST nudge split across both scores)
```

Key constants (`priors.py`): `LEAGUE_TEAM_PPG=25.9`, `MATCHUP_RESPONSE=1.40` (W1 softened ×0.90 → **1.26**), `EXPECTED_POINTS_CLAMP=(7,55)`.

Early-season uncertainty widens **`margin_sd` only** — it does **not** haircut PPG / expected points.

### KEI layer

`apply_cfb_kei` (`cfb_kei.py`):

| Field             | Source                                                |
| ----------------- | ----------------------------------------------------- |
| `model_total`     | `proj.model_total` / `expected_total`                 |
| `kei_total`       | **`_round(model_total)` — identity**                  |
| `kei_spread_home` | `model_spread` **+** `apply_bias_guard` (early weeks) |

There is **no** totals branch in `apply_bias_guard`. Drivers logged for totals are empty of any total delta.

### Pack → Edge Board

1. Builder `scripts/cfb/build_cfb_kei_futures_2026.py` → `project_game_preview` → `apply_cfb_kei` → writes `apps/web/lib/data/cfb-kei-w0-w1-2026.json` with pack `used_in_spread: true`.
2. Web `kei-lines.ts` `cfbKeiLinesFromBundledPack` maps `handicapTotal` / `projTotal` ← `kei.kei_total`, `modelTotal` ← `model_total`.
3. `build-edge-board-rows.ts` → `mergeKeiIntoEdgeBoardRows` paints Total row `kei` from `projTotal`.
4. `EdgeBoard.tsx` Tag O/U: `signedOUEdge = keiTotal − bestTotal`, then CFB cuts PLAY ≥ 4.0 / LEAN ≥ 2.5.

### Is KEI total == model total?

**Yes, exactly.** On the W1 FBS pack (n=43): `max |model_total − kei_total| = 0`. Reproject through current universe reproduces pack totals to 0.00.

**Why Model column shows "—":** UI only paints Model when `modelKei !== kei` (`EdgeBoard.tsx`). Spreads diverge (bias guard); totals never do. Page copy is correct: _"Tags never use Model vs market"_ — for totals that is moot because they are the same number.

---

## 2. Any totals bias guard / hist-cal / haircut on the live path?

| Layer                                                     | Spreads                                                                              | Totals                                  |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------- | ------------------------------------------------ | ------ |
| `apply_bias_guard` (`cfb-bias-guard-v1-histcal-20260805`) | Yes (W0–2)                                                                           | **No**                                  |
| `margin_calibration.apply_calibrated_scores`              | Research / power-SoT Bernoulli path only; `used_in_spread=false`; **keeps midpoint** | Explicitly does not retarget totals     |
| `project_game` (KEI builder path)                         | Raw strength→scores                                                                  | Raw strength→scores — **no margin cal** |
| Trusted market `                                          | market−KEI                                                                           | ≥12`                                    | Yes (`applyCfbTrustedMarketToRows`, Spread only) | **No** |
| NFL-style totals calibrator                               | n/a                                                                                  | **Not present for CFB**                 |

### Since when?

- Docs already said totals were **"coherent with scores but not market-calibrated"** (`data/ops/cfb-projection-calibration-20260804.md`).
- Hist-cal 2026-08-05 fixed hist totals bias (+3.2 → −0.5) by dropping `LEAGUE_TEAM_PPG` 27.5→25.9 **under league-average roster/QB proxy** — not a published KEI totals haircut (`data/ops/cfb-historical-calibration-20260805.md`).
- Engine package still says do not invent KEI until a later calibrated pass (`cfb_season_engine/__init__.py`), but the W0/W1 pack shipped `used_in_spread=true` anyway (`build_cfb_kei_futures_2026.py`, rules doc). That is a **product stamp choice**, not a totals formula change.
- Nothing in the live KEI→board path ever applied a totals haircut. Nothing was "dropped" — **it was never built**.

---

## 3. What drives +8 vs street this week?

Ops card W1 totals with KEI + book (n=43):

| Stat                          |                     Value |
| ----------------------------- | ------------------------: | ----- | -------------------------- |
| Mean KEI total                |                     60.67 |
| Mean market                   |                     52.55 |
| Mean KEI − market             |                 **+8.12** |
| Overs / Unders (sign of diff) |                    37 / 6 |
| Card tags                     | PLAY 32 · LEAN 5 · PASS 6 |
| `                             |                      diff | ≥ 12` | **11**, all still **PLAY** |

(Live board counts Ryan quoted — 33/3/1 Over tags — are the same failure mode; card is the in-repo stamp.)

### Counterfactual decomposition (reproject, same universe as builder)

Holding street mean fixed and zeroing one multiplicative term at a time:

| Term neutralized        | Mean gap vs street |                   Δ from +8.12 |
| ----------------------- | -----------------: | -----------------------------: |
| (actual)                |              +8.12 |                              — |
| matchup ratio → 1       |          **+2.16** |                      **−5.96** |
| unit offense boost → 1  |              +7.21 |                          −0.90 |
| unit defense dampen → 1 |              +9.12 |     +1.00 (dampen was cooling) |
| pace → 1                |              +8.30 | +0.18 (pace slightly **cool**) |
| HFA+coach+ST off        |              +5.75 |                  −2.37 add-ons |
| `2 × LEAGUE_TEAM_PPG`   |               51.8 |            **−0.75 vs street** |

**Base PPG is not the problem.** Street ~52.6 ≈ `2×25.9`. The model gets hot after **(off/def)^response** lifts the favorite’s scoring more than it suppresses the dog.

Observed W1 matchup ratios (post soft-clamp, response already applied): home mean **1.258**, away **0.932**, average **1.095**. Cupcake / mismatch games print the loudest totals because the favorite’s offense vs weak defense ratio is large while the underdog still clears ~league PPG vs a good D.

### Pace / explosiveness

- Mean pace factor **0.996** (min 0.94 / max 1.05) — not an explosion.
- Mean explosiveness proxy **~49.8** — near neutral; only a tiny pace nudge (`(expl−50)/400`).

### Roster/QB vs power-SoT fill

| Slice                                              |   n | Mean KEI−mkt |
| -------------------------------------------------- | --: | -----------: |
| Both sides `hierarchical_compose` (roster/QB path) |  35 |    **+8.46** |
| Either side `power_sot_v0.15_fill`                 |   8 |        +6.62 |

Fill is **not** the Over-drunk story. All 11 `|diff|≥12` loud games are full compose (FIU@USF, MRSH@PSU, TULN@DUKE, BOISE@ORE, …).

### Cupcake vs peer

| Bucket (`     | model spread |     `) | n   | Mean diff |
| ------------- | -----------: | -----: | --- | --------- |
| Peer `<10`    |           14 |  +4.64 |
| Mod 7–14      |           14 |  +6.52 |
| Big 14–21     |           10 | +12.10 |
| Cupcake `≥21` |           12 |  +9.96 |
| Cupcake `     |            s |   ≥17` | 16  | +11.89    |

Mismatches amplify the gap, but **peers are still ~+4.5 Over**. CoS guess holds: missing totals calibration + no haircut, not "a couple of cupcake blowouts."

### Top movers (ops card)

| Game      |  KEI |  Mkt |  Diff | Tag  |
| --------- | ---: | ---: | ----: | ---- |
| FIU@USF   | 72.5 | 52.5 | +20.0 | PLAY |
| MRSH@PSU  | 72.9 | 53.5 | +19.4 | PLAY |
| TULN@DUKE | 70.3 | 51.5 | +18.8 | PLAY |
| BOISE@ORE | 68.0 | 51.5 | +16.5 | PLAY |
| M-OH@PITT | 64.2 | 48.5 | +15.7 | PLAY |
| TXST@TEX  | 76.1 | 60.5 | +15.6 | PLAY |
| MOST@TAMU | 68.4 | 53.5 | +14.9 | PLAY |
| BC@CIN    | 64.3 | 49.5 | +14.8 | PLAY |
| OHIO@NEB  | 61.1 | 47.5 | +13.6 | PLAY |
| UTEP@OU   | 64.3 | 51.0 | +13.3 | PLAY |
| MASS@RUT  | 64.7 | 51.5 | +13.2 | PLAY |

Only Under lean of note: FAU@UF ≈ −2.6 LEAN (card). Rest of Unders are PASS / thin.

### Why hist-cal didn’t save 2026 live totals

Hist-cal graded seasons with **league-average roster/QB proxies**. Live 2026 uses **real ESPN roster + QB + units + SP+ carry**, which widens O/D ratios. Same `MATCHUP_RESPONSE=1.40` that decompresses spreads then **re-inflates sum-of-scores** on those ratios. Early uncertainty widens σ for WP/spreads but leaves PPG untouched — week-1 uncertainty does **not** damp totals.

---

## 4. Bug vs expected uncalibrated model?

Checked and **discarded** as primary cause:

| Hypothesis                        | Finding                                                                                                                                                        |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PPG double-count                  | Unit boosts still apply after indices that already blend OL/skill; compose claims anti-double-count via **reduced** weights. Net boost×dampen ≈ 0.99 — not +8. |
| Pace / explosiveness explosion    | Mean pace &lt; 1; expl ~50.                                                                                                                                    |
| Power-SoT fill without roster     | 8/43 games; cooler than compose mean.                                                                                                                          |
| Home/away total sign              | Totals are unsigned sums; OU edge = KEI − market. Correct.                                                                                                     |
| Units (per-team PPG summed wrong) | `total = home + away`; identity with scores. Correct.                                                                                                          |
| Garbage-time                      | Player-script knobs affect allocation only, not team scores.                                                                                                   |
| Wrong formula / missing clamp     | Clamp (7,55)/side present; loud games sit inside it.                                                                                                           |

**Conclusion:** expected **uncalibrated** research totals published as KEI (`kei_total := model_total`), plus a **tagger hole** on `|12|`. Not a broken adder.

---

## 5. Why Tag O/U still prints PLAY at `|diff|≥12`

### Spreads (gate works)

`cfb-trusted-market.ts`:

- `CFB_ABSURD_VS_KEI_PTS = 12`
- `applyCfbTrustedMarketToRows` runs **only when `row.market === "Spread"`** — Total rows return unchanged.
- `EdgeBoard` spread edge requires `cfbTrusted`; untrusted → no edge → PASS.

House rules (`data/ops/cfb-kei-rules-2026.md`) state absurd vs KEI → untrusted PASS for the board generally; implementation is **spread-scoped**.

### Totals (gate was missing — fixed 2026-09-01)

Was:

```text
signedOUEdge = keiTotal − bestTotal   // no trustCfbMarket
```

Now Total rows get the same absurd / single-book trust flags; Tag O/U requires `cfbTotalTrusted` (KEI + book still painted).

---

## 6. Recommendations

### (a) Sit `|12|` as PASS on totals — **implemented 2026-09-01**

Tagger now applies `CFB_ABSURD_VS_KEI_PTS=12` (+ single-book 8) to Total rows in `cfb-trusted-market.ts`; `EdgeBoard` Tag O/U requires `cfbTrusted` like spreads. KEI pack unchanged — no haircut / recut.

### (b) Leave KEI totals stamped this week

Do not recut, haircut, or chase street. Stamp-at-pull doctrine stands. Model/KEI identity for totals is honest given current code.

### (c) What a later calibration would mean

Not “retune PPG to this week’s books.” A real totals cal would be something like:

1. Holdout on historical closes **with the same identity stack** used live (or an explicit delta for roster/QB vs hist proxy).
2. Separate **totals** residual (level + maybe mismatch interaction), versioned like the spread bias guard — applied only at KEI publish, `used_in_spread` documented.
3. Keep research `model_total` fair; let `kei_total` diverge when a measured guard exists (mirrors spreads).
4. Do **not** conflate with margin-scale (midpoint-preserving) or with Tag thresholds.

Until that exists, board honesty for Overs is: **PASS the absurd band in the tagger**, and treat KEI totals as research-coherent scores, not market-calibrated O/U.

---

## File index (evidence)

| Path                                                                           | Role                                                     |
| ------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `services/model-service/src/services/cfb_season_engine/team_projection.py`     | `expected_team_points`, `project_game` total = home+away |
| `services/model-service/src/services/cfb_season_engine/priors.py`              | PPG, MATCHUP_RESPONSE, early soften / margin_sd          |
| `services/model-service/src/services/cfb_season_engine/cfb_kei.py`             | `kei_total = model_total`; bias guard spread-only        |
| `services/model-service/src/services/cfb_season_engine/margin_calibration.py`  | Margin only; totals untouched                            |
| `scripts/cfb/build_cfb_kei_futures_2026.py`                                    | Pack mint; `used_in_spread=true`                         |
| `apps/web/lib/data/cfb-kei-w0-w1-2026.json`                                    | Live KEI pack                                            |
| `apps/web/lib/kei-lines.ts` / `edge-board-kei.ts` / `build-edge-board-rows.ts` | Pack → board                                             |
| `apps/web/lib/cfb-trusted-market.ts`                                           | Absurd gate; Spread **and** Total rows (totals unsigned) |
| `apps/web/components/EdgeBoard.tsx`                                            | OU edge/tag gated on cfbTrusted; Model hide-when-equal   |
| `data/ops/cfb-kei-rules-2026.md`                                               | House rules (PLAY 4 / LEAN 2.5 / \|12\|)                 |
| `data/ops/cfb-w1-handicap-card-20260831.json`                                  | Stamped W1 KEI vs Best totals                            |
| `data/ops/cfb-historical-calibration-20260805.md`                              | Hist totals bias; PPG cut; no KEI totals guard           |
| `data/ops/cfb-projection-calibration-20260804.md`                              | “coherent with scores but not market-calibrated”         |
