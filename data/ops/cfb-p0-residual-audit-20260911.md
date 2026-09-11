# CFB P0 residual audit — post structural repair

**Date:** 2026-09-11  
**Branch:** `cursor/cfb-model-repair-1bf8`  
**Continues:** #532 NAME_TO_CODE restore  
**Kill switch:** `CFB_EDGE_BOARD_PUBLIC_ENABLED=false` — **KEEP DARK**

No coefficient change, no clipping, no market shrinkage, no Vegas retune,
no Odds API ingest change. Market join is an ESPN scoreboard snapshot
(DraftKings lines, 2026-09-11, n=85) used only to measure residuals.

## Root cause (closed)

`NAME_TO_CODE` dropped 11 official FBS names, including **Missouri → MIZZ**.
Packaging then sat those teams as `Independent` with **null power**. The KEI
builder silently hydrated `offense_index or 1.0` / `defense_index or 1.0`.
Missouri @ Kansas was priced as if MIZZ were a replacement-level Independent
(~16-pt KU favorite) against a market of **MIZ −4.5**.

Missouri State **MOST** was already mapped and is distinct (CUSA, SP+ −10.7).

## What this pass adds on top of #532

- Joined residual audit script: `scripts/cfb/cfb_joined_residual_audit.py`
- Projections-desk overlay for the 11 P0 codes: conference + finite power
  from power SoT. Season-win totals stay **unminted** (`season_wins_unminted`)
  — no invented E[wins].
- CI now runs `tests/test_cfb_name_to_code_fail_closed.py`

## Stamps (after)

| Surface | version / as_of |
|---|---|
| KEI pack header | `cfb-kei-v1.0-2026w2` / `2026-09-10` |
| KEI `generated_at` | `2026-09-11T03:41:46Z` |
| Research power / projections / futures | `2026-08-31` week0-close (intentional) |
| Engine | `cfb-season-engine-v0.15-power-sot` (frozen) |

Before (deploy-vercel): KEI header still said `cfb-kei-v1.0-2026w0` / `2026-08-31` while the pack already contained W2 games.

## Focus games vs ESPN/DK (home-signed)

### Missouri @ Kansas

| | Model | KEI | Market | Spread residual (KEI−mkt) | Favorite vs market |
|---|---|---|---|---|---|
| **Before** | KU −15.62 | KU −16.82 | KU **+4.5** (MIZ −4.5) | **−21.32** | **FLIP** (data bug) |
| **After** | KU +1.10 | KU +1.85 | KU +4.5 | **−2.65** | agree (Mizz fav) |
| Totals | 61.56 → 58.32 | same | 51.5 | +10.06 → **+6.82** | — |

### Rutgers @ Boston College

| | Model | KEI | Market | Spread residual | Favorite vs market |
|---|---|---|---|---|---|
| **Before** | BC +12.49 | +13.49 | BC **−3** | **+16.49** | FLIP |
| **After** | BC +12.49 | +13.49 | BC −3 | **+16.49** | FLIP (unchanged) |
| Totals | 63.29 | 63.29 | 53.5 | **+9.79** | — |

RUT and BC were never in the P0 null-power set. This is **genuine model vs market**, not a mapping bug.

## W2 FBS–FBS joined slate (n=47 / 47)

| Metric | Before (null-power hydrate) | After (mapped + fail-closed) |
|---|---|---|
| spread MAE | 6.774 | 6.857 |
| total MAE | 9.724 | 10.236 |
| median spread residual | +2.94 | +2.90 |
| median total residual | +8.49 | +9.14 |
| mean total residual | +9.33 | +9.94 |
| favorite flips vs market | 11 | 11 |
| \|gap\| ≥ 7 / 10 / 14 / 20 | 21 / 10 / 6 / **1** | 20 / 12 / 8 / **0** |
| null-power count (SoT) | 11 P0 | **0** |

Fleet spread MAE is not the success metric. The one 21-pt data-bug game
(MIZZ@KU) left the ≥20 bucket. UNT (P0) now has real AAC power and
**UNLV@UNT flipped** (before UNLV fav +10.87 KEI vs market UNLV −3;
after UNT −15.61). That is a revealed model disagreement, not a leftover
null hydrate.

Repair-induced KEI sign flips vs the broken pack: **MIZZ@KU**, **UNLV@UNT**.

## Team-level outliers after (mean \|spread residual\|)

UNLV/UNT 18.61 · RUT/BC 16.49 · USF/ARMY 16.35 · WKU/UGA 15.27 · LT/LSU 15.01 · SDSU/UCLA 14.90

## Totals inflation (still present)

`kei_total` remains an identity copy of `model_total`. W2 mean residual
**+9.9** / median **+9.1** vs ESPN/DK. Same diagnosis as
`docs/CFB_TOTALS_HOT_AUDIT.md`: matchup-response score inflation, no
totals bias guard. **Not** a NAME_TO_CODE defect. Do not haircut or
retune in this pass. Totals PLAY stays sat.

## Fail-closed / honesty

- Zero silent `or 1.0` hydrates on the builder / power SoT path
- Zero P0 Independent leftovers in power SoT
- Missing required features raise `MissingRequiredTeamFeature`
- Public kill switch cannot be flipped on via env
- No invented KEI / PLAY / season-win totals for P0

## Validation verdict

**Structural repair: ACCEPT.**  
**Public residuals: KEEP DARK.**

Do not reactivate CFB Edge Board. Remaining favorite flips and ~10-pt
total bias are model/calibration questions, not missing-map packaging.
Ryan / Validation must sign off before `CFB_EDGE_BOARD_PUBLIC_ENABLED`
can flip.

Parked (not this PR): Railway `weeks=` for NFL slate; CFB totals
calibrator / spread prior (separate, frozen-math-breaking).
