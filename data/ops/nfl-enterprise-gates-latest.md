# NFL Enterprise Gates

Generated: 2026-07-28T20:55:31.241697+00:00
Overall: **RED**
Betting-product ready: **False**
Selective PLAY ready: **False**
Grading: `data/ops/nfl-kav-grading-after.json`
Supervised: `data/ops/nfl-kav-supervised-retrain-v3.json`
PLAY holdout: `data/ops/nfl-play-only-holdout.json`

| Check | Status | Detail |
| --- | --- | --- |
| `ats_vs_minus_110` | RED | Full-slate ATS below −110 breakeven — selective segments only. |
| `clv_spread_sample` | RED | CLV +rate below floor despite adequate sample. |
| `mae_vs_market_close` | GREEN | Model beats market close MAE on spread and total. |
| `supervised_holdout` | GREEN | Chronological holdout within floors. |
| `owned_open_close_coverage` | GREEN | Owned open/close game coverage for CLV densify track. |
| `props_stake_policy` | GREEN | Props must remain research-only / stake-off until holdout clears. |
| `play_only_holdout` | YELLOW | Spread PLAY ATS clears −110 on unused 2025 boards, but CLV fails or sample thin. Do NOT claim subscription GREEN / ~60% until CLV clears. |

## Notes

- PLAY ATS looks strong on 2025 boards but CLV does not clear — treat as research / paper until live CLV confirms; do not market 60%.
- Do NOT claim betting-product ready. Ship selective PASS-default publish gates and keep improving ATS/CLV samples.
- Full-slate ATS failed — publish PLAY only on segments that clear nfl_side_total_publish_policy evidence.
- PLAY-only unused holdout not GREEN — keep NFL_PRODUCT_GATE_STATUS conservative; PASS default remains mandatory.

## Selective publish examples

- candidate=PLAY → tag=PASS stake=False (product_gate_red)
- candidate=PASS → tag=PASS stake=False (product_gate_red)
- candidate=PLAY → tag=PASS stake=False (product_gate_red)
- candidate=PASS → tag=PASS stake=False (product_gate_red)

