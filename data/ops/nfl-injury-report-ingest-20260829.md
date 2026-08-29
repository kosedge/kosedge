# Week-of injury report ingest (2026-08-29)

**After #306 defense accepts.** #307 (rest/weather feed) may still be open — this leg does not depend on it.

## Contract

- `scripts/nfl/ingest_injury_report.py` — Sleeper `GET /v1/players/nfl` (cache gitignored, TTL ~1.5h)
- DNP / LP / FP / Out from Sleeper injury + practice fields
- **T1** only if starter **or** `snap_share_prior >= 0.40` **and** (Out/IR **or** 2× DNP) **and** pack still full-go
- `proposed_patch` only; `confirmation=low` unless official Out/IR (`high`)
- CLI: `queue_camp_sot_flags.py --scan-report` / `--queue-report`; `--alert-t1` includes `source=sleeper`
- Idempotent key `(player_id, event, as_of_date)`
- **No auto-accept**

## Files

- `services/model-service/src/services/nfl_injury_report_scan.py`
- `scripts/nfl/ingest_injury_report.py`
- `scripts/nfl/queue_camp_sot_flags.py`
- `tests/test_nfl_injury_report_scan.py`

## Out of scope

Accepts, defense pack edits, weather feed, txn scanner rewrite.
