# Aug 25 Factor Freeze — Operator Checklist

**Freeze date:** 2026-08-25  
**Canonical policy:** `data/ops/nfl-factor-freeze-aug25.md`  
**Gates doc:** `docs/NFL_ENTERPRISE_GATES.md`

## Env / config (Railway model-service)

| Variable | Expected | Notes |
| --- | --- | --- |
| `NFL_PRODUCT_GATE_STATUS` | `YELLOW` | RED forces all PASS |
| `NFL_PRESEASON_MODE` | `info` | Blocks season PLAY on PRE |
| `NFL_FACTOR_TRAVEL_WEATHER` / H | ON | Promoted |
| `NFL_FACTOR_ERROR_REGIME` / D | ON | Promoted (uncertainty only) |
| E info velocity | OFF | Do not opt-in |
| B personnel | OFF | Do not opt-in |
| A coach aggression | OFF | Do not opt-in |
| Visual Crossing key | set | Weather path on Railway |
| `TOTAL_PLAY_ENABLED` | false (code) | Sides-only |
| Props `PLAY_STAKE_ELIGIBLE` | false (code) | Research only |

## Pre-freeze day checks

- [ ] Ablation artifacts still show E/B/A kill (`nfl-second-order-ablation.md`)
- [ ] PLAY band still `[2.5, 7.0)` — no widen PR open
- [ ] Paper book tracker runs clean (`nfl-paper-book-latest.md`)
- [ ] Fair-lines returns `publish_tag_spread` / PRE → PASS
- [ ] Projections hub Actual column pipeline ready (`write_projection_actuals.py --from-db`)
- [ ] No unauthorized blend-weight retune

## Unfreeze (only with holdout)

1. Pre-register candidate + holdout seasons  
2. Confirmatory PLAY holdout + ablation green  
3. Update freeze doc + enterprise gates  
4. Then flip env/code
