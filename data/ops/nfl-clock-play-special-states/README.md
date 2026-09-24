# Explicit sack and special-teams possession states

This train-only layer adds missing football opportunity states:

- pass → sack, with field loss, clock, down/distance, and safety branch;
- punt → blocked-punt state, recovery/return branch, and special possession;
- existing state-triggered return TD/safety layer consumes the resulting
  football opportunities.

The layer does not alter offensive scoring probabilities, red-zone state
transitions, fourth-down policy/continuation, clock-flow priors, FG make
rates, timeout policy, or OT.

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_special_state_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-special-states/special-state-priors.json
```
