# Tracked SQL migrations (`infra/db`)

Numbered Postgres DDL for the model-service warehouse lives here.
History is **immutable**: never edit a file that has already been applied
(or baselined) in any shared environment. Add a new `NNN_*.sql` instead.

## Runner (source of truth)

Package: `services/model-service/src/db_migrations`  
CLI (from `services/model-service`):

```bash
python -m src.db_migrations check-integrity
DATABASE_URL='…' python -m src.db_migrations status
DATABASE_URL='…' python -m src.db_migrations apply   # alias: up
DATABASE_URL='…' python -m src.db_migrations baseline \
  --through 054 --confirm-baseline 054 --expect-database "$DBNAME"
```

`DATABASE_URL` is **environment-only** — there is no `--database-url` flag.
Never commit credentials; never log the URL.

From monorepo root:

```bash
python scripts/db/migrate.py check-integrity
DATABASE_URL='…' python scripts/db/migrate.py status
# KosEdge prod cutover (054 already live — stamp only, do not re-apply):
# DBNAME=$(psql "$DATABASE_URL" -Atc 'select current_database()')
# DATABASE_URL='…' python scripts/db/migrate.py baseline \
#   --through 054 --confirm-baseline 054 --expect-database "$DBNAME"
# DATABASE_URL='…' python scripts/db/migrate.py status --require-current
```

### Tracking table (bootstrap DDL — not a numbered migration)

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  version integer PRIMARY KEY,
  filename text NOT NULL,
  checksum text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now(),
  duration_ms integer NOT NULL,
  CONSTRAINT schema_migrations_filename_unique UNIQUE (filename),
  CONSTRAINT schema_migrations_checksum_sha256
    CHECK (checksum ~ '^[0-9a-f]{64}$'),
  CONSTRAINT schema_migrations_duration_nonneg
    CHECK (duration_ms >= 0)
);
```

### Behavior

| Command                                                            | Effect                                                                  |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| `check-integrity`                                                  | Repo-only: refuse duplicate/gap/unparseable names. No DB.               |
| `status`                                                           | List applied / pending / drifted; validates history when nonempty.      |
| `apply` / `up`                                                     | Advisory-locked; apply pending in order; stop on first failure.         |
| `baseline --through N --confirm-baseline N --expect-database NAME` | Stamp `1..N` without SQL. Empty tracker only. Explicit tokens required. |

Hard rules:

- Numeric order by integer version (`9` before `10` before `054`).
- Sequence must be contiguous `1..N` (no gaps, no duplicates).
- Mutating commands take a stable Postgres advisory lock (bounded timeout, then fail).
- Nonempty tracking history must be an exact contiguous prefix `001..N` matching
  disk on **version + filename + checksum**. A tracker with only `054` refuses
  apply (does not execute `001`–`053`).
- Checksum/filename drift, missing files, rogue rows, or holes → refuse.
- **Unbaselined legacy DB** (any non-system user object: table/view/matview/sequence
  in any schema, with empty/missing tracker) → `apply` **loudly refuses**.
- Baseline never fills holes; never runs implicitly.

## Adding a migration

1. Next integer after the current max (`ls infra/db \| tail`).
2. Name: `NNN_short_snake_description.sql` (zero-pad to 3 digits by convention).
3. Prefer idempotent DDL where practical (`IF NOT EXISTS`, guarded alters).
4. Do **not** put `schema_migrations` DDL in a numbered file.
5. Run `python scripts/db/migrate.py check-integrity`.
6. Apply in the target DB with the runner (not ad-hoc `psql` for new work).

## Status

```bash
DATABASE_URL='…' python scripts/db/migrate.py status
DATABASE_URL='…' python scripts/db/migrate.py status --require-current
```

`--require-current` exits non-zero on pending, drifted, invalid history, or
unbaselined legacy. `status` always runs the same history validation when the
tracker is nonempty.

## Applying

```bash
DATABASE_URL='…' python scripts/db/migrate.py apply
# or
DATABASE_URL='…' python scripts/db/migrate.py up
DATABASE_URL='…' python scripts/db/migrate.py apply --dry-run
```

Fresh empty database: runner bootstraps `schema_migrations`, then applies
`001…N`. Already current: clean no-op.

## Baselining an existing database (production cutover)

**Baseline proves migration history by operator attestation.** It does **not**
inspect whether each historical DDL effect exists on the database.

Production already had numbered SQL applied by hand with **no** tracker,
including migration `054` (nullable `confidence` on
`nfl_player_prop_model_edges`). Verified ~2026-09-03: `is_nullable=YES`,
`column_default=NULL`; `schema_migrations` absent; ~85,388 edge rows; do
**not** re-apply 054.

Exact cutover for **this** warehouse:

```bash
# 1) Confirm high-water mark (054 already live; tracker missing).
DBNAME=$(psql "$DATABASE_URL" -Atc 'select current_database()')

# 2) Explicit baseline through 054 (stamps only — no SQL replay).
#    --confirm-baseline must equal --through; --expect-database must equal DBNAME.
DATABASE_URL='…' python scripts/db/migrate.py baseline \
  --through 054 --confirm-baseline 054 --expect-database "$DBNAME"

# 3) Confirm current (nothing pending). Do NOT run apply for 054 again.
DATABASE_URL='…' python scripts/db/migrate.py status --require-current
```

Initial baseline is only allowed when `schema_migrations` is empty. Hole-filling
of partial history is refused (needs a separate explicitly guarded repair path).

Never run a normal `apply` against an untracked nonempty DB — it will refuse
rather than replay `001`–`054`. After baselining through 054, `apply` is a
clean no-op until a future `055+` lands.

## Checksum / history drift response

If `status` fails history validation or apply raises drift/integrity errors:

1. **Do not** “fix” by editing old SQL files or deleting tracking rows casually.
2. Restore file bytes from git to match recorded checksums, **or**
3. Add a **new** forward migration for intended schema changes.
4. Treat rewritten history as an incident; do not use `baseline` to fill holes.

## Deploy / CI — what is and is not verified

| Check                                          | Where                                                             | Connects to prod? | DDL? |
| ---------------------------------------------- | ----------------------------------------------------------------- | ----------------- | ---- |
| Sequence + discoverability (`check-integrity`) | PR Checks / Deploy                                                | No                | No   |
| Unit + disposable-Postgres integration tests   | PR Checks (service)                                               | No                | No   |
| Live `status --require-current`                | Deploy Railway **only when** `MIGRATION_STATUS_GATE_ENABLED=true` | Read-only URL     | No   |
| Auto-apply on deploy                           | **Never**                                                         | —                 | —    |

**Cutover phase (first merge):** leave `MIGRATION_STATUS_GATE_ENABLED` unset/false
so Deploy Railway can ship the runner without circular dependency on an
unbaselined warehouse. After runner deploy + production baseline through 054,
set the Actions variable to `true` and configure read-only
`WAREHOUSE_DATABASE_URL`. If the URL is absent while the gate is enabled, CI
fails honestly — it does not fake live schema validation.

Railway images stage a copy via
`scripts/db/stage_migrations_into_model_service.sh` (`/app/infra/db`) so
operators can run the CLI inside the service context. Staging does **not**
apply migrations.

## Historical note

Older go-live docs used `psql -f infra/db/NNN_….sql` and one-off
`scripts/*/apply_*_prod.py` helpers. Prefer this runner for all new work;
keep those scripts only as historical references.
