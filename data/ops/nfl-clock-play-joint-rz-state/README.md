# Joint clock-flow / red-zone state process

This train-only Gate 1 candidate combines two locally validated mechanisms on
the clean clock-flow parent:

1. non-fourth red-zone rush next-state transitions; and
2. red-zone fourth-down action priors.

It does not alter clock-flow priors, pass transitions, non-red-zone behavior,
timeout policy, OT, or any scoring parameter.

Build the fourth-down decision priors:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_rz_fourth_decision_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-joint-rz-state/rz-fourth-decision-priors.json
```

Sparse RZ fourth-down state cells pool action probabilities to a
red-zone-only field-bucket parent using 30 pseudo-decisions.
