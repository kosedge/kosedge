# Clock-Play joint pre-entry pass/RZ continuation

This artifact owns exactly one handoff: when the pass route immediately before
a drive's first red-zone snap starts at offensive yardline 70–79, that first
non-fourth red-zone pass or rush is drawn from its joint train-only route and
continuation prior. The simulator applies it after an eligible generic pass
crosses from 70–79. It does not change the generic pass crossing rate, later
red-zone snaps, fourth-down decisions, possession transitions, clock priors,
seeds, or certification thresholds.

Build the 2013–2023 regular-season prior from the locked owned PBP source:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_pre_entry_pass_rz_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-pre-entry-pass-rz/pre-entry-pass-rz-priors.json
```

Freeze the unchanged 2,048-game structural schedule:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/run_clock_play_baseline_v1.py \
  --config data/ops/nfl-clock-play-pre-entry-pass-rz/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --output-dir /tmp/nfl-clock-play-pre-entry-pass-rz-freeze \
  --source-sha <candidate-sha>
```

Run train-only historical certification:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/certify_clock_play_v1_1.py \
  --config data/ops/nfl-clock-play-pre-entry-pass-rz/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --historical-pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output /tmp/nfl-clock-play-pre-entry-pass-rz-certification.json
```
