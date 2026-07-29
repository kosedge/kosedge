# NFL Hard Model Pass — Week-1

Generated: 2026-07-29

## Decision: **NO blend / PLAY recal**

Holdout evidence does **not** clear a re-tune:

- Selective spread PLAY (`spread_play_v2_cap7`) already GREEN on confirmatory 2024–25.
- Second-order ablation killed E/B/A; H+D stay on.
- Totals confirmatory CLV RED → sides-only, not a totals recal.
- Props remain research-only (`PLAY_STAKE_ELIGIBLE=false`).

## Left unchanged

| Knob | Status |
| --- | --- |
| `NFL_MARKET_BLEND_SPREAD_WEIGHT` | Locked (default 0.30) |
| PLAY band | `[2.5, 7.0)` |
| E/B/A factors | OFF |
| Props stake | false |

## When to revisit

Only after a pre-registered unused holdout beats locked v2 on ATS **and** movement-CLV with adequate n. Do not chase full-slate 60%.
