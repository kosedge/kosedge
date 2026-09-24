# Clock-Play RZ pass-approach transition candidate

## Pre-code contract

- **Hypothesis:** the remaining RZ-entry surplus is directly caused by the
  coarse `opponent_territory` pass-outcome key combining starts from the
  opponent 50 through 21. The trace shows that starts at the opponent 30–21
  cross into the RZ at 37.20% in the repaired simulator versus 34.48% in
  2013–23 train PBP. A separate train-only pass-outcome key for those
  70–79-yardline starts can correct that transition without changing play-call
  selection or any RZ route.
- **Parent and receipt:** `e311ce547ed8f61ab1817caa64850cb5838f29f0`; four
  frozen root seeds × 512 replicates (2,048 games); train PBP SHA
  `823304baa68961187307c1d08774bee80a58d9757ee57be01f6879b34c5bca2c`.
- **Change:** split only `pass_state_key` for starts at yardlines 70–79 and
  rebuild only the pass-outcome prior consumed by the candidate config.
- **Frozen:** called-play probabilities, designed-rush priors, RZ-rush
  transitions, fourth-down and FG decisions, special-teams priors, clock
  flow, possession semantics, seed schedule, and certification thresholds.

The candidate is accepted only if the 70–79 pass-to-RZ crossing rate moves
toward the train rate, every route remains exclusive, all state invariants
pass, and it does not create a structural regression in the frozen
non-pass subsystems. It is rejected if correcting this entry interface
requires a call-rate, rush, fourth-down, or special-teams change.

Build the candidate prior:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_coherent_state_priors.py \
  --pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-rz-pass-approach-fix/pass-approach-state-priors.json
```
