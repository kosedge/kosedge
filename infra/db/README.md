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
DATABASE_URL='…' python -m src.db_migrations baseline --through 054
DATABASE_URL='…' python -m src.db_migrations stamp --through 054   # alias
```

From monorepo root:

```bash
python scripts/db/migrate.py check-integrity
DATABASE_URL='…' python scripts/db/migrate.py status
# KosEdge prod cutover (054 already live — stamp only, do not re-apply):
# DATABASE_URL='…' python scripts/db/migrate.py baseline --through 054
# DATABASE_URL='…' python scripts/db/migrate.py status --require-current
```

Uses the model-service `psycopg` dependency. Pass the URL via env or
`--database-url`. **Never commit credentials.**

### Tracking table

Bootstrapped by the runner (not a numbered migration — that would be a
chicken-and-egg dependency):

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  version integer PRIMARY KEY,
  filename text NOT NULL UNIQUE,
  checksum text NOT NULL,          -- SHA-256 hex of file bytes
  applied_at timestamptz NOT NULL DEFAULT now(),
  duration_ms integer NOT NULL     -- 0 when stamped via baseline
);
```

### Behavior

| Command | Effect |
| --- | --- |
| `check-integrity` | Repo-only: refuse duplicate/gap/unparseable names. No DB. |
| `status` | List applied / pending / drifted. Optional `--require-current`. |
| `apply` / `up` | Apply pending in numeric order; stop on first failure; no-op if current. |
| `baseline` / `stamp --through N` | Record versions `<= N` **without executing SQL**. Explicit only. |

Hard rules:

- Numeric order by integer version (`9` before `10` before `054`).
- Sequence must be contiguous `1..N` (no gaps, no duplicates).
- Checksum drift on an applied row → refuse apply (do not rewrite history).
- **Unbaselined legacy DB** (public tables present, no tracking rows) →
  `apply` **loudly refuses**. Never baseline implicitly.

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

`--require-current` exits non-zero on pending, drifted, or unbaselined legacy.
It does not apply DDL (optional `--bootstrap-tracking` only creates the empty
tracker table when you explicitly ask).

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

Production already had numbered SQL applied by hand with **no** tracker,
including migration `054` (nullable `confidence` on
`nfl_player_prop_model_edges`). Verified ~2026-09-03: `is_nullable=YES`,
`column_default=NULL`; `schema_migrations` absent; do **not** re-apply 054.

Exact cutover for **this** warehouse:

```bash
# 1) Inspect / confirm high-water mark (what is already live).
#    Expect objects through 054, including nullable confidence without default.
#    Expect schema_migrations to be missing.

# 2) Explicit baseline through 054 (stamps only — no SQL replay, no apply).
DATABASE_URL='…' python scripts/db/migrate.py baseline --through 054

# 3) Confirm current (nothing pending). Do NOT run apply for 054 again.
DATABASE_URL='…' python scripts/db/migrate.py status --require-current

# Optional sanity (already verified in prod — re-check only if unsure):
# SELECT is_nullable, column_default
# FROM information_schema.columns
# WHERE table_schema = 'public'
#   AND table_name = 'nfl_player_prop_model_edges'
#   AND column_name = 'confidence';
# Pass: is_nullable = YES AND column_default IS NULL.
```

Never run a normal `apply` against an untracked nonempty DB — it will refuse
rather than replay `001`–`054`. After baselining through 054, `apply` is a
clean no-op until a future `055+` lands.

## Checksum drift response

If `status` shows `drifted` or apply raises checksum drift:

1. **Do not** “fix” by editing the old SQL file to match production.
2. Restore the file bytes from git history to the recorded checksum, **or**
3. Add a **new** forward migration that performs the intended schema change.
4. If someone rewrote history on purpose, treat it as an incident: reconcile
   file vs database, then re-baseline only with explicit operator approval.

## Deploy / CI — what is and is not verified

| Check | Where | Connects to prod? | DDL? |
| --- | --- | --- | --- |
| Sequence + discoverability (`check-integrity`) | PR Checks / Deploy Railway | No | No |
| Live `status --require-current` | Deploy Railway **only if** secret `WAREHOUSE_DATABASE_URL` is set | Read-only URL | No (status gate) |
| Auto-apply on deploy | **Never** | — | CI must not get arbitrary production DDL |

If `WAREHOUSE_DATABASE_URL` is unset and the push changes `infra/db/*.sql`,
Deploy Railway **fails loudly** so a deploy cannot quietly leave SQL pending.
CI cannot invent live schema validation without that URL — it will say so.

Railway images stage a copy via
`scripts/db/stage_migrations_into_model_service.sh` (`/app/infra/db`) so
operators can run the CLI inside the service context. Staging does **not**
apply migrations.

## Historical note

Older go-live docs used `psql -f infra/db/NNN_….sql` and one-off
`scripts/*/apply_*_prod.py` helpers. Prefer this runner for all new work;
keep those scripts only as historical references.
