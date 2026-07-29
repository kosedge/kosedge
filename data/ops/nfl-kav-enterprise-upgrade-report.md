# NFL KAV Enterprise Upgrade Report

Generated: 2026-07-28  
Branch: `nfl-kav-sharpen`  
DB: `127.0.0.1:5432/kosedge` (promoted restore warehouse)

## Executive verdict

**Betting-product ready: NO (gates RED).**  
Honest model score: **6.7 / 10** (prior ~5.5). Selective PASS-default publish is shipped; full-slate ATS/CLV still miss subscription “every-game edge” bar.

## 1) What was done

| Pillar | Deliverable |
| --- | --- |
| Supervised v3 + KAV | Active fit schema 3, 41 features incl. KAV; holdout n=570 — `data/ops/nfl-kav-supervised-retrain-v3.json` |
| 2025 re-sim | 97 days, **370 games**, 500 sims — `data/ops/nfl-kav-resim-summary.json` |
| Owned OC densify 2020–23 | **~6,022 credits**; owned OC games 724 → **1,931** — `data/ops/nfl-owned-oc-densify-2020-2023.*` |
| Selective publish | Python + Edge Board + fair-lines API tags; LEAN spread disabled; total PLAY only [2.5,3.0) |
| Enterprise gates | `docs/NFL_ENTERPRISE_GATES.md`, evaluator, tests (6 py + 4 vitest) |
| Restored missing odds persister | `scripts/odds/persist_mainline_odds.py` from `7bab07a7` |

## 2) Before → after metrics

Sources: `nfl-kav-grading-before.json` → `nfl-kav-grading-after.json`

| Metric | Before | After | Δ |
| --- | ---: | ---: | ---: |
| Spread MAE | 9.613 | **9.551** | −0.062 |
| Total MAE | 10.123 | **10.086** | −0.037 |
| ML Brier | 0.200 | **0.193** | −0.006 |
| ATS hit | 0.493 | 0.495 | +0.002 |
| CLV spread n | 159 | **601** | +442 |
| CLV spread +rate | 66.0% | 50.9% | densify diluted |
| CLV total n | 117 | **378** | +261 |
| Owned OC games | 724 | **1,931** | densify |

Market close MAE (after): spread 9.776 / total 10.296 — model still beats market on both.

### Supervised chronological holdout (schema v3)

| | Train | Holdout |
| --- | ---: | ---: |
| Brier | 0.120 | **0.148** |
| Margin MAE | 6.80 | **7.48** |
| Total MAE | 8.84 | **9.20** |
| Rows | 2992 | 570 |

Holdout gate: **GREEN** (floors cleared). Blend retune earlier today **not promoted** (totals regress).

## 3) Gate status

Artifact: `data/ops/nfl-enterprise-gates-latest.md`

| Check | Status |
| --- | --- |
| ATS vs −110 | **RED** (0.495 < 0.5238) |
| CLV spread sample | **RED** (n=601 OK, +rate 50.9% < 55%) |
| MAE vs market | **GREEN** |
| Supervised holdout | **GREEN** |
| Owned OC coverage | **GREEN** |
| Props stake-off | **GREEN** |
| **Overall / betting-product** | **RED / false** |

Selective PLAY still allowed under product gate YELLOW on Edge Board for historically clearing bands (spread ≥2.5; total 2.5–3.0). Product claim remains forbidden while overall RED.

## 4) Score now: **6.7 / 10**

Strict scale: 10 = institutional Vegas-competitive every-game; 7 = chargeable selective edge; 5.5 prior.

Why not 7+: densified CLV +rate ~51% and full-slate ATS still below breakeven.  
Why above 5.5: KAV in live path + v3 holdout green, MAE edge vs close, CLV n in hundreds, selective publish + go/no-go infra shipped.

## 5) Gap list to ~9.5 (priority)

1. **Tag-level unused holdout** for spread PLAY (≥2.5) and narrow total PLAY on 2025 KAV boards — confirm ATS/CLV before marketing.
2. **Raise tagged CLV +rate ≥55%** (or shrink publish universe to books/windows that clear).
3. **Special-teams KAV** + better injury/inactives near kickoff.
4. **Totals path** — adaptive calibrator + avoid failed blend promotion; cut toxic ≥3.0 total PLAY (already PASS).
5. **Props** — keep stake-off until densified pass MAE ≤12 and holdout clears.
6. **Prod promote** — run same retrain/resim/gates against Railway warehouse; merge `nfl-kav-sharpen` when ready.

## 6) Needs from user

- Confirm whether to **commit** this branch’s new gate/publish/densify scripts + ops artifacts.
- **Do not push/PR** unless asked.
- Optional: raise Odds API spend only if further OC densify gaps appear (2020–23 mainlines done; ~3.0M credits remain).
- Prod DB already has local kosedge = restored warehouse; sync/promote to Railway when deploying.
