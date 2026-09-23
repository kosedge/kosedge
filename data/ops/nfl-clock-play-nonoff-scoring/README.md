# Non-offensive scoring architecture

This train-only layer adds football-state scoring branches without changing the
offensive core:

- turnover return TD;
- kickoff return TD;
- punt return TD;
- blocked-kick return TD; and
- safety after a backed-up play crosses the offense’s goal line.

All branches use 2013–2023 regular-season PBP opportunity-conditional rates.
They score through the existing try/kickoff transition (return TD) or safety
free-kick transition, never through a post-hoc points draw.

Build the event priors:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_non_offensive_scoring_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-nonoff-scoring/non-offensive-scoring-priors.json
```
