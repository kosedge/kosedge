# NFL Totals Band Review — Week-1 Launch Posture

Generated: 2026-07-29  
Source: `data/ops/nfl-play-only-holdout.md` (confirmatory 2024–25)

## Confirmatory check (totals PLAY `2.5 ≤ |edge| < 3.0`)

| Slice | n | ATS | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Primary 2025 total | 30 | 0.700 | 25 | 0.400 | **RED** |
| Confirmatory 2024–25 total | 52 | 0.6154 | 43 | 0.3488 | **RED** |

Spread PLAY on the same confirmatory sample is **GREEN** (ATS 73.1%, CLV+ 61.2%, n_clv=206).

## Decision

**Launch posture: sides-only.**

- `TOTAL_PLAY_ENABLED = False` in `nfl_side_total_publish_policy.py` and web mirror.
- Publish reason: `totals_sides_only_launch`.
- Narrow band constants retained for research re-enable after a GREEN confirmatory CLV sample.
- Do **not** widen total PLAY; do **not** market totals as subscription PLAY.

## Re-enable criteria (pre-registered)

1. Confirmatory movement-CLV+ ≥ 55% with n_clv ≥ 40 (prefer ≥ 60).
2. ATS ≥ 52.38% with n ≥ 60.
3. Explicit flip of `TOTAL_PLAY_ENABLED` + enterprise gates re-eval.
