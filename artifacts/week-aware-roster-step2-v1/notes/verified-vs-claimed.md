# Verified vs claimed

Filled after the harness run. Pre-testing this file records the split rule.

## Verified (only after receipts exist)

- Expected answers commit precedes harness sha (order).
- T-PIT-1..10 compared to `leakage/expected/` on synthetic 2098.
- Development coverage counted from `dev_game_keys_le2023.json` without
  opening 2024/25 and without refitting.

## Claimed (not verified as production truth)

- No week-aware source SoT is pinned.
- Reconstructible = 0 is a coverage fact (NR-1), not a model score.
- K-*/I-* gates are unchanged; this package does not re-measure them.
- Season-level C-1 pins stay SUPERSEDED; they are not re-certified.
