# NFL as the enterprise model standard (t4141u)

Correctness over speed. No seal deadline.

## What this change does

1. **Operate week ≠ research pin.** `scripts/nfl/nfl_operate_week.py` reads the
   canonical 2026 pack and returns the last REG week whose every kickoff is
   already in the past. `run_weekly_operate.py` no longer skips ingest because
   `nfl-web-launch-bundle.json` is still `preseason: true`.
2. **B0 and post-week grade are first-class stages.** They refuse to invent
   fairs or results. Missing file-backed inputs ⇒ fail/skip with flags.
   After kickoff the only honest label is `RETROSPECTIVE`.
3. **Local inputs** (`nfl_local_inputs.py`) are sha-pinned, freshness-checked,
   and completeness-checked. Silent `rest=7.0` / `injury=0.0` / `index=1.0`
   are refused.
4. **Computation trace** (`nfl_computation_trace.py`) names every hop from
   schedule through the Edge Board. Missing hops stay missing.
5. **n=2998 is retracted.** Closest committed train n is 2992. The 570-row
   tail is CONTAMINATED for certification. Do not invent a 6-game drop list.

## What this change does not do

- Does **not** enable the Tuesday GitHub cron or Railway Beat. Platform
  Reliability owns scheduling, monitoring, and deploy.
- Does **not** merge, deploy, or talk to prod DB / Odds / Railway from CI.
- Does **not** flip `nfl-web-launch-bundle.json`.
- Does **not** ungate `WEEKLY_PROPS_LIVE` or PLAY tags.
- Does **not** edit frozen Lab protocol / threshold files.
- Does **not** fabricate retrospective pregame B0 numbers.

## Invoke (local / workflow_dispatch)

```bash
python scripts/nfl/run_weekly_operate.py --dry-run            # resolve week from schedule
python scripts/nfl/run_weekly_operate.py --week 6 --dry-run   # named finished week
```

`--dry-run` writes only the last-run JSON path you pass (`--last-run`).
Default last-run path is `data/ops/nfl-weekly-operate-last.json` — do not
commit a live receipt unless it is an honest dry-run artifact you intend
to keep. Prefer `--last-run` under `/tmp` or `/var/tmp`.

## Preserve

Certified Lab protocol, PLAY lock, kav v3 JSON, and enterprise gate files
are read, not rewritten.
