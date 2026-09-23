# Non-fourth red-zone rush transition experiment

This train-only candidate replaces only non-fourth `run` transitions at the
opponent 20-yard line and closer. It preserves clock flow, pass outcomes,
fourth-down decisions and continuation, FG decisions, timeout policy, OT,
scoring outside this rush state, and all non-red-zone behavior.

The implementation branch was created only after the locked historical
denominator, exclusive-routing, parent receipt, and train-window receipts
passed.

Build train-only rush next-state priors:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_rz_rush_transition_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-rz-rush-transition/rush-transition-priors.json
```

State cells are `field bucket × down × yards-to-go × goal-to-go`. Sparse cells
pool outcomes to a red-zone-only `field × down × goal-to-go` parent using 30
pseudo-rushes; outcome-specific yards pool with 12 pseudo-rushes.
