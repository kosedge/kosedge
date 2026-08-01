# HFA 1.025 force-resim grade (2026-08-01)

**Deploy:** Railway model-service after PR #50 (`7a468ad8` / merged `4675a206`).  
**Resim task:** `1e0a8de4-58c8-4d9c-8d63-a078251cb006` — force_resim May–Jul densify, **628** games, no Odds densify.  
**Leakage:** repaired **22** rows; walkforward/quality **leakage_violations=0**.

## Before / after (densify-window grades)

| Metric | After 1.035 (PR #48) | After 1.025 + leakage/SP/matchup | Δ |
|--------|---------------------:|--------------------------------:|--:|
| Walkforward n | 778 | 778 | — |
| **Base Brier (ML)** | 0.250502 | **0.249888** | −0.0006 |
| Calibrated Brier | 0.251474 | 0.251474 | 0 |
| Base MAE totals | 3.5128 | 3.514 | +0.001 |
| **ECE** | 0.027706 | **0.016728** | −0.011 |
| **ML CLV** | +0.00702 | **+0.00681** | −0.0002 |
| Total CLV | +0.09293 | +0.0914 | −0.0015 |
| Spread / RL CLV | +0.1118 | +0.07453 | −0.037 |
| Leakage violations | 11 | **0** | −11 |

Resim-embedded holdout: base Brier **0.249103**, leakage **0**, MAE 3.463.

## Verdict

- Leakage fix: **pass** (0).
- Brier: slight improvement vs 1.035, still above 0.24 gate.
- ML CLV: **no recovery** at 1.025 (still ~+0.007 vs pre-HFA +0.023).
- Next ablation step: **HFA off (1.0)** to test whether CLV returns without the global home mul (keep SP/matchup/leakage ships).

Props remain `research_only`. Unused holdout still frozen for stake.
