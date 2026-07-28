# NFL Enterprise Gates

Generated: 2026-07-28T21:11:49.766911+00:00
Overall: **RED**
Betting-product ready: **False**
Selective PLAY ready: **True**
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
| `play_only_holdout` | GREEN | Confirmatory spread PLAY (v2 band, movement-CLV) clears ATS + CLV product floors. |

## Notes

- Do NOT claim betting-product ready. Ship selective PASS-default publish gates and keep improving ATS/CLV samples.
- Selective PLAY holdout GREEN — chargeable wedge is PLAY-tagged sides only, not full-slate.
- Full-slate ATS failed — publish PLAY only on segments that clear nfl_side_total_publish_policy evidence.

## Selective publish examples

- candidate=PLAY → tag=PASS stake=False (product_gate_red)
- candidate=PASS → tag=PASS stake=False (product_gate_red)
- candidate=PLAY → tag=PASS stake=False (product_gate_red)
- candidate=PASS → tag=PASS stake=False (product_gate_red)

