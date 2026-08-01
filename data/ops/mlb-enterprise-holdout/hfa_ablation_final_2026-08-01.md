# HFA ablation final choice (2026-08-01)

## Production densify grades (same lookback methodology)

| HFA | Base Brier | ML CLV | ECE | Leakage | Notes |
|----:|-----------:|-------:|----:|--------:|-------|
| 1.035 | 0.250502 | +0.00702 | 0.0277 | 11 | PR #48 alone |
| **1.025** | 0.249888 | **+0.00681** | **0.0167** | **0** | + leakage/SP/matchup |
| 1.0 | 0.248963 | +0.00564 | 0.0223 | 0 | CLV worse vs 1.025 |

## Decision

**Ship `HOME_FIELD_OFFENSE_MUL = 1.025`.**

- 1.035 rejected as failed CLV trade (and left leakage dirty until repair).
- 1.0 improves Brier slightly but **hurts** ML/RL CLV further → not a CLV recovery.
- Pre-HFA +0.023 CLV remains unrecovered; next levers are matchup/SP/feature stack ablation, not another HFA bump.

## Ops

Restore 1.025 on Railway and force-resim densify window so production projections match the chosen constant.
