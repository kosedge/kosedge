# CFB Projection Calibration (v0.6.1)

**Branch:** `feat/cfb-projection-calibration` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.6.1-calibration`  
**Date:** 2026-08-04  
**Baseline metrics:** `data/ops/cfb-calibration-20260804/`

## Goal

Make team ratings, spreads, totals, and season win projections more realistic and better aligned with recent CFB reality — without rewriting layers or touching the ESPN 2026 real-roster overlay.

## What was wrong (v0.6 baseline)

| Symptom | Evidence |
| --- | --- |
| Top offense compression | **33 / 130** teams piled at `STRENGTH_CLAMP` upper = **1.55** |
| Inflated QB proxies | MAC/G5 `incumbent` / talent proxies hit **1.55** QB index → power-conference-looking offense (e.g. NIU) |
| Soft blue-blood vs G5 spreads | UGA–BALL W1 **−19.2**; OSU–EMU W1 **−12.6**; TEX–NMSU W5 **−11.4** |
| Season win ranking absurdity | NIU mean wins **#1** (~8.5) ahead of ALA; densified SOS + soft mismatches |
| Defense index compression | Def stdev **0.094** vs offense **0.202** |

Fidelity remained honest (`approximate`); this pass is **measured sanity calibration**, not market-grade CLV / KEI.

## Knobs changed (priors / compose / matchup)

| Knob | Before | After | Intent |
| --- | --- | --- | --- |
| `ENGINE_VERSION` | `v0.6-real-roster` | `v0.6.1-calibration` | Version bump |
| `STRENGTH_CLAMP` | `(0.55, 1.55)` | `(0.52, 1.68)` | Decompress top O pile-up |
| `QB_SITUATION_INDEX_CLAMP` | *(shared STRENGTH_CLAMP)* | `(0.62, 1.38)` | Stop MAC QB proxies inventing P4 offense |
| `QB_INDEX_BLEND` | `0.40` | `0.32` | Reassert roster/units vs QB |
| `QB_CLASS_OFFENSE_MULT` incumbent | `1.10` | `1.06` | Temper ceiling inflation |
| `QB_CAST_INDEX_SCALE` | `0.14` | `0.11` | Milder cast amp |
| `SCORE_TO_INDEX_DIVISOR` | `80` (hardcoded) | `68` | Steeper roster/unit → index |
| `MATCHUP_RESPONSE` | `1.08` | `1.22` | Stronger O/D → spread |
| `MATCHUP_RATIO_CLAMP` | `(0.60, 1.32)` | `(0.55, 1.42)` | Allow clearer cupcake favorites |
| `MATCHUP_RATIO_EXCESS_RETAIN` | `0.40` | `0.50` | Keep ordering past soft cap |
| `DEF_UNIT_BLEND` | `0.22` | `0.28` | Widen defense separation |
| `UNIT_*_SCALE` | `0.10` / `0.12` | `0.11` / `0.14` | Slightly stronger unit matchup |
| `EARLY_SEASON_SEPARATION_SOFTEN` W1 | `0.74` | `0.82` | Uncertainty via margin_sd, not mushy favorites |

**Preserved:** real-roster snapshot wiring; HFA buckets; coaching week-decay; early-season wider `margin_sd`; layer module boundaries; NFL untouched; Edge Board markets-only.

## Before / after (packaged 2026 universe)

### Strength ladder

| Metric | Before | After |
| --- | --- | --- |
| Offense clamp hits (at ceiling) | **33** @ 1.55 | **5** @ 1.68 |
| Power index spread (max−min) | 0.513 | **0.598** |
| Power stdev | 0.135 | **0.152** |
| NIU offense_index | 1.445 | **1.298** (QB capped 1.38) |
| Roster strength min/max | 50.4 / 73.1 | unchanged (roster overlay intact) |

### Project-game samples

| Matchup | Before spread / total / hWP | After |
| --- | --- | --- |
| BALL@UGA W1 | −19.2 / 60.0 / 0.815 | **−24.5 / 60.2 / 0.874** |
| EMU@OSU W1 | −12.6 / 66.6 / 0.724 | **−19.6 / 69.7 / 0.823** |
| NMSU@TEX W5 | −11.4 / 72.0 / 0.775 | **−21.3 / 72.3 / 0.921** |
| BALL@PSU W1 (new HC) | −14.1 / 62.3 / 0.742 | **−20.4 / 64.1 / 0.827** |
| ALA@UGA W5 | +1.7 / 63.1 / 0.455 | +2.6 / 59.2 / 0.432 (still toss-up) |
| MICH@OSU W5 | −4.1 / 67.9 / 0.607 | −4.1 / 70.0 / 0.607 |
| TEX@OSU margin_sd W1 vs W5 | W1 wider | **still wider** (~21 vs ~15) |

Spreads stay inside the soft blowout band (tests: favorites **< −10** and **> −36** vs BALL).

### Season wins (80 paths, seed 42)

| Metric | Before | After |
| --- | --- | --- |
| Mean wins min–max | 3.45–8.47 | 3.26–8.70 |
| Cross-team mean stdev | 1.16 | **1.31** |
| Within-team wins std (mean) | ~2.05 | ~2.09 |
| #1 by mean wins | NIU | **ALA** (NIU still high — SOS soft spot) |

## Soft spots remaining

1. **Densified schedule SOS** — G5/MAC teams still post high win totals vs weak paths; official FBS slate needed before ranking-ish standings are trustworthy.
2. **UGA power rank** — moderate ESPN QB talent proxy keeps UGA below TEX/OSU/ALA in thin power ladder; not a roster bug.
3. **EMU vs BALL** — portal QB talent proxy still overrates some G5 offenses in head-to-heads.
4. **Totals** — coherent with scores but not market-calibrated (no closing-line study yet).
5. **No Edge Board KEI** — intentional; markets-only until fair lines are market-grade.
6. **Historical backtest** — this pass is forward sanity vs recent CFB intuition, not 2022–2025 graded calibration.

## Tests

`services/model-service/tests/test_cfb_season_engine.py` (+ real-roster):

- Blue-blood vs G5 ordering + spread/total bounds
- Offense ceiling pile-up bound (`≤ 12` at clamp)
- Season win distribution width bounds
- Early-season wider `margin_sd`
- HFA bucket + new-HC early penalty still material

## UI

- `/pro/cfb/model` — badge **CFB calibrated**; live `engine_version` from status
- `/pro/cfb/project-game` — shows calibration engine version string

## Deploy checks

```bash
# model-service
curl -sS "$MODEL_SERVICE_URL/cfb/season-engine/status" | jq .engine_version
# expect: cfb-season-engine-v0.6.1-calibration

# web
curl -sS https://www.kosedge.com/api/ping
# then /pro/cfb/model shows new engine version once Railway + Vercel catch up
```
