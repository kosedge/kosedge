# Exact RO DATABASE_URL / warehouse access blocker (t4564u / Alex db42ad49)

CERT_CANDIDATE=0. RESEARCH only. NFL NO-GO. Do not invent warehouse rows.

## Probe (this VM, 2026-10-27)

| Check | Result |
| --- | --- |
| `DATABASE_URL` env | **UNSET** |
| `LAUNCH_RESEARCH_DATABASE_URL` env | **UNSET** |
| `127.0.0.1:5432` | **not accepting** (`ConnectionRefusedError`) |
| `railway` CLI | **not installed** |
| `psycopg` / `psycopg2` | **not installed** |
| `materialize_team_rolling_features.py --dry-run --seasons 2013,2014` | **FAIL** `Could not inventory DB` |
| Railway MCP `list-variables` model-service `e0c54f94-3ee0-41c0-8081-e96d3e246a4a` | name `DATABASE_URL` present; **value hidden** (OAuth connected-app) |
| Railway MCP `list-variables` Postgres `4d1abc93-e819-4926-98a0-82feb43b3280` | names `DATABASE_URL`, `DATABASE_PUBLIC_URL` present; **values hidden** |
| Project | KosEdge `da3d68f8-d925-462f-b262-c4ef3e488245` / production `4bf00465-0220-4764-8b3b-e7adce18ca64` |

## Repro

```bash
echo "DATABASE_URL=${DATABASE_URL:-UNSET}"
python3 -c "import socket; socket.create_connection(('127.0.0.1',5432),0.4)"
python3 scripts/nfl/materialize_team_rolling_features.py --dry-run --seasons 2013,2014
```

Cannot INSERT/SELECT `nfl_dp_team_rolling_features_weekly` 2013–2022. Warehouse coverage in `HISTORICAL_OOS_DIAGNOSTIC` is 2023–2026 only.

## What this does **not** authorize

Inventing Postgres rows. Writing to production Railway. Claiming an offline CSV is the warehouse table.
