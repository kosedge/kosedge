# HFA ablation — HOME_FIELD_OFFENSE_MUL (2026-08-01)

## Policy

Treat **1.035 as a failed CLV trade** after densify-window production grade (ML CLV +0.023 → +0.007). Prefer holdout/walkforward evidence over cosmetics. No Odds densify.

## Synthetic grid (local, n=100 games × 2000 sims, home prior 0.54, market 0.535)

| HFA | avg P(home) | avg total | Brier | CLV proxy |
|----:|------------:|----------:|------:|----------:|
| 1.035 | 0.5399 | 9.051 | **0.248471** | −0.00275 |
| **1.025** | 0.5269 | 9.049 | 0.249645 | −0.00485 |
| 1.02 | 0.5203 | 9.057 | 0.250753 | −0.00624 |
| 1.0 (off) | 0.4991 | 9.070 | 0.256108 | −0.01195 |

Script: `scripts/mlb/eval_hfa_ablation.py` (also saved JSON beside this note).

## Selection

**Winner: 1.025**

- Excludes 1.035 per production CLV regression.
- Keeps most of the Brier gain vs HFA-off (0.2561 → 0.2496).
- Mean home ~0.527 (slightly under historical 0.54; real slate SP/offense features lift further).
- Totals stay nearly neutral across candidates.

## Shipped with

Leakage stamp repair (lookback-wide), SP identity coverage, batter–pitcher matchup mul, weather reliability when wind missing. Force-resim + walkforward/CLV grade is the production confirmation.
