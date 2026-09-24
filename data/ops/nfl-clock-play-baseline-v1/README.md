# Clock-Play Baseline v1

This is an isolated NFL experiment, not a production model binding. It is a
new play/drive state loop with down, distance, possession, field position,
clock, post-score kickoff, timeout/endgame, and regular-season overtime
transitions.

It is not an alias for any prior R11, R11R, V33, or external clock-play label.
The existing season engine remains a snapshot/script ancestor only. Its
committed kicker-layer constants are consumed solely for XP and field-goal
make-rate priors.

`inputs.json` intentionally contains four synthetic structural cases. It has
no actual results, market lines, historical play-by-play, held-out data, or
calibration targets. The resulting metric packet reports structural checks,
not spread/total MAE or key-number metrics.

Freeze command (replace `<SOURCE_SHA>` with the source commit):

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_clock_play_baseline_v1.py \
  --config data/ops/nfl-clock-play-baseline-v1/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --output-dir data/ops/nfl-clock-play-baseline-v1/freeze \
  --source-sha <SOURCE_SHA>
```

The runner writes deterministic JSON only: a seed manifest, command receipt,
source/config/input hashes, structural metric packet, traces/probes, and
artifact checksums. It writes no timestamps or production-facing data.
