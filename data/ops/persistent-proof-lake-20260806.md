# Persistent Proof Lake — Ops Note (2026-08-06)

## Where data lives

| Environment | Backend | Location |
|-------------|---------|----------|
| **Railway production** | `postgres` (auto when `DATABASE_URL` set) | Postgres table `proof_projections` |
| **Local dev** | `jsonl` (no `DATABASE_URL`) or `postgres` | `services/model-service/data/ops/projection_logs/projections.jsonl` or DB |

Confirm via **`GET /proof/docs`**:

- `backend`: `postgres` or `jsonl`
- `lake_dir`: `postgres://proof_projections` or filesystem path
- `lake_health`: row count when healthy

## Durability

- **Postgres**: survives Railway redeploys and container restarts. Same database as other model-service features.
- **JSONL**: ephemeral on Railway (`/app` or `/tmp`); dev/fallback only. Do not rely on JSONL in production.

## Environment

| Variable | Values | Notes |
|----------|--------|-------|
| `PROOF_LAKE_BACKEND` | `postgres` \| `jsonl` \| `auto` | **`auto`** (default): postgres if `DATABASE_URL` present, else jsonl |
| `PROJECTION_LOG_BACKEND` | legacy alias | Same as above |
| `DATABASE_URL` | Postgres connection string | Required for durable production lake |

## Bootstrap / migration

On first Postgres use when `proof_projections` is empty:

1. Import rows from unified JSONL (`PROJECTION_LOG_DIR` / default lake path), idempotent by `id`
2. Import rows from legacy `cfb_projection_logs` table if present

DDL: `infra/db/050_proof_projections.sql` (also applied at runtime via `ensure_proof_projections_table`).

## Backup / restore

- **Backup**: standard Postgres backups (Railway automated backups + any org DR policy). Table: `proof_projections`.
- **Restore**: restore Postgres snapshot; proof records return with the rest of the DB. No separate lake restore step.
- **JSONL export** (optional): copy `projections.jsonl` for local inspection; not the production source of truth when backend is postgres.

## Fail modes (honest behavior)

| Condition | Writes (`POST /proof/projections`) | Reads (`GET /proof/performance`, calibration) |
|-----------|-----------------------------------|-----------------------------------------------|
| Postgres up | Persisted; `storage: postgres` | Normal counts and reports |
| Postgres down, backend=postgres | Log warning; `storage: failed:postgres` | `ok: false`, error `proof lake unavailable` — **not** fake zero counts |
| JSONL fallback (dev) | File append/rewrite | Reads from JSONL file |

## Verify after deploy

1. `GET /proof/docs` → `backend: postgres`, `table: proof_projections`
2. `POST /proof/projections` for NFL + CFB smoke rows; note `id`s
3. `GET /proof/performance?sport=nfl` and `?sport=cfb` → `n_logged >= 1`
4. After Railway redeploy: repeat step 3; counts must not reset to zero
5. Optional SQL: `SELECT sport, COUNT(*) FROM proof_projections GROUP BY sport;`

## Railway branch

Model-service deploys from Railway project `joyful-clarity`, service `kosedge`. Code reaches Railway via the branch Railway tracks (typically **`deploy-vercel`** after merge). Ensure this change is on that branch before expecting production Postgres persistence.

## Related docs

- Unified proof API: `data/ops/unified-proof-layer-20260806.md`
- Historical calibration: `data/ops/historical-calibration-reports-20260806.md`
