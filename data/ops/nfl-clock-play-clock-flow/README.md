# Clock-Play clock-flow calibration

This train-only candidate changes elapsed clock only. It preserves scoring,
terminal possession outcome, fourth-down, red-zone, timeout, and OT
parameters from Clock-Play v1.2.

Build the PBP clock-flow priors:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_clock_flow_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-clock-flow/clock-flow-priors.json
```

The builder measures within-drive core-snap intervals by play kind. Conditional
means are shrunk with 100 parent pseudo-intervals, then normalized to the
locked historical seconds-per-core-snap denominator. This is a timing
calibration, not a scoring or possession-outcome calibration.
# Clock-Play clock-flow calibration

This train-only candidate changes elapsed time only. It does not alter scoring,
terminal possession outcomes, fourth-down policy/continuation, red-zone
transitions, timeout decisions, or OT policy.

Build PBP-derived within-drive clock intervals:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_clock_flow_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-clock-flow/clock-flow-priors.json
```

Intervals are measured from a core snap to the next core snap in the same
fixed drive. Conditional means are shrunk to the all within-drive core
interval parent with 100 pseudo-intervals, then normalized to the locked
historical seconds-per-core-snap denominator.
