# Clock-Play coherent designed-rush states

This isolated train-only candidate replaces the inherited Gaussian yard draw,
explosive-play overlay, and independent turnover branch for designed rushes
outside the opponent 20. Every selected designed rush resolves through one
primary outcome: touchdown, lost fumble, first down, loss, zero gain, or
short gain. A lost fumble owns its direct defensive return transition.

The pass-state family remains separate. Non-fourth red-zone rushes retain
priority for the committed red-zone rush transition family; fourth-down
decisions and continuation retain priority over this family. Clock flow and
punt, field-goal, and kickoff routing are unchanged.

Build the sole prior artifact from the 2013–23 regular-season subset:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_designed_rush_state_priors.py \
  --pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-coherent-rush-states/designed-rush-state-priors.json
```

Freeze with committed synthetic inputs:

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_clock_play_baseline_v1.py \
  --config data/ops/nfl-clock-play-coherent-rush-states/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --output-dir /tmp/nfl-clock-play-coherent-rush-states-freeze \
  --source-sha <candidate-sha>
```
