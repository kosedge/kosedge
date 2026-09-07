# Holdout fixtures (PR A)

Tiny **synthetic** CI fixtures only. Not production holdout raw.

| File | Purpose |
|---|---|
| `espn_scoreboard_fixture_day.json` | One sanitized ESPN-shaped day for schema/smoke tests |
| `espn_scoreboard_fixture_day.sha256` | Content hash of that fixture |

Bulk ESPN scoreboard payloads live in private R2 (`espn_schedule_raw_v1`). Sealed packages + the canonical 2024–25 schedule pack are **path-B rebuildable** from that governed raw plus in-repo KenPom/odds — see `docs/ops/ncaam/PHASE_26F_REBUILD_AND_SEAL_SEMANTICS.md` and `scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py`. Do not manually place hash-only seal artifacts.

Do not commit raw archive days here.
