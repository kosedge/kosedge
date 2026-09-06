# Holdout fixtures (PR A)

Tiny **synthetic** CI fixtures only. Not production holdout raw.

| File | Purpose |
|---|---|
| `espn_scoreboard_fixture_day.json` | One sanitized ESPN-shaped day for schema/smoke tests |
| `espn_scoreboard_fixture_day.sha256` | Content hash of that fixture |

Bulk ESPN scoreboard payloads, model-ready packages (`features.json` / `labels.json`), and large audit row dumps live in private R2 — see governance PR B (`data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/`).

Do not commit raw archive days here.
