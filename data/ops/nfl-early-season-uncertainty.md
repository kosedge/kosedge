# Early-Season Uncertainty Posture (W1–W4)

**Status:** Locked for 2026 Week-1 launch  
**Style:** Factor **D** (`error_regime`) — uncertainty widen / confidence penalty  
**Not:** 50% market blend, PLAY-band widen, or E/B/A re-enable

## Behavior

| Week | Early-season boost (relative) | Effect |
| --- | --- | --- |
| 1 | Full (`early_season_regime_boost` ≈ 0.18) | Max stdev widen + confidence cut |
| 2–3 | Decaying | Still cautious |
| 4 | ~half of W1 | Exit ramp |
| 5+ | Off | Normal D signals only |

Code: `compute_error_regime_uncertainty(..., season_week=)` in
`nfl_second_order_factors.py`, wired via `kav_as_of_week` /
`second_order_as_of_week` in the handicapping framework.

## Product implications

- Selective PLAY still allowed when edge clears `spread_play_v2_cap7`.
- Operators should **size down** when confidence is depressed — not chase volume.
- Totals remain sides-only; props research-only.

## Honesty

This is not a claim that W1 edges are “calibrated like Week 10.” It is an
explicit uncertainty posture until the rolling sample thickens.
