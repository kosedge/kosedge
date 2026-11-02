# Exact RO DATABASE_URL / warehouse access blocker (t4564u / Alex db42ad49)

CERT_CANDIDATE=0. RESEARCH only. NFL NO-GO.

## Probe (this VM, 2026-10-27)

| Check | Result |
| --- | --- |
| `DATABASE_URL` env | **UNSET** |
| `LAUNCH_RESEARCH_DATABASE_URL` env | **UNSET** |
| `127.0.0.1:5432` | **not accepting** (`ConnectionRefusedError`) |
| `pg_isready` | not installed |
| `materialize_team_rolling_features.py --dry-run --seasons 2013,2014` | **FAIL** `Could not inventory DB. last_err=No module named 'psycopg2'` (no `psycopg`/`psycopg2` on this VM; env DSN unset; local `5432` down) |
| Railway MCP `list-variables` model-service (`e0c54f94-3ee0-41c0-8081-e96d3e246a4a`) | name `DATABASE_URL` **present**; **value hidden** (OAuth connected-app: names only) |
| Railway MCP `list-variables` Postgres (`4d1abc93-e819-4926-98a0-82feb43b3280`) | names `DATABASE_URL`, `DATABASE_PUBLIC_URL` **present**; **values hidden** |
| Project | KosEdge `da3d68f8-d925-462f-b262-c4ef3e488245` / production `4bf00465-0220-4764-8b3b-e7adce18ca64` |

## Repro

```bash
echo "DATABASE_URL=${DATABASE_URL:-UNSET}"
python3 -c "import socket; socket.create_connection(('127.0.0.1',5432),0.4)"
python3 scripts/nfl/materialize_team_rolling_features.py --dry-run --seasons 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022
```

Expected: materialize exits `Could not inventory DB` (no DSN). Railway MCP does not return the connection string to this agent.

## What this blocks

Official `nfl_dp_team_rolling_features_weekly` 2013–2022 backfill via `data_platform_nfl.cli` (Alex db42ad49). Warehouse coverage in `HISTORICAL_OOS_DIAGNOSTIC` is 2023–2026 only.

## Bypass used for emit

Public nflverse `stats_team_week` 2012–2023, last-5 completed REG weeks, **strict** `(season,week) < target` (no current-week leakage). Not warehouse SoT.

COS order file `COS_ORDER_CURSOR_t4564u_EPA_WF_FEATURE_EMIT_v1.txt` sha8 `65b1c0fb` was not in Slack / Linear / Notion / this repo. §2 column order reconstructed from walkforward_export_82ffb211 `FIELDNAMES` EPA block + join keys.
