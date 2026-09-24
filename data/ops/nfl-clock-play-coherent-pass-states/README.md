# Clock-Play coherent pass and special-teams states

This isolated, train-only candidate replaces the generic pass branch with
exactly one called-pass outcome: completion, incompletion, sack, scramble,
interception, or lost fumble. It separately owns punt, field-goal, and
kickoff transitions, including returns, return touchdowns, blocked punts,
field-goal blocks, and safeties reached through an end-zone state.

The candidate retains the committed clock-flow, red-zone rush transition, and
red-zone fourth-down decision priors. Designed non-red-zone rushes remain in
their inherited state family. No market data, held-out data, production
binding, R14 result, or score-target calibration is used.

Build the sole prior artifact from the 2013–23 regular-season subset:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_coherent_state_priors.py \
  --pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-coherent-pass-states/coherent-state-priors.json
```

Freeze with the committed synthetic inputs:

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_clock_play_baseline_v1.py \
  --config data/ops/nfl-clock-play-coherent-pass-states/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --output-dir /tmp/nfl-clock-play-coherent-pass-states-freeze \
  --source-sha <candidate-sha>
```
