"""Apply / baseline / status for numbered SQL migrations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .discovery import MigrationFile, discover_migrations
from .errors import (
    BaselineConfirmationError,
    BaselineRequiredError,
    ChecksumDriftError,
    HistoryIntegrityError,
    MigrationApplyError,
    MigrationError,
    MigrationLockError,
)

# Bootstrap is deliberate and NOT a numbered migration. The runner requires this
# table before it can track anything; creating it via 055-style SQL would nest a
# chicken-and-egg dependency on the tracker itself.
SCHEMA_MIGRATIONS_DDL = """
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
""".strip()

TRACKING_TABLE = "schema_migrations"

# Stable session advisory-lock key for kosedge schema migrations.
# Must not collide with ad-hoc locks elsewhere; fixed constant is intentional.
ADVISORY_LOCK_KEY = 874_201_935
DEFAULT_LOCK_TIMEOUT_SECONDS = 30

# Non-system namespaces excluded from "user object" detection.
_SYSTEM_SCHEMAS = ("pg_catalog", "information_schema", "pg_toast")


class MigrationState(str, Enum):
    APPLIED = "applied"
    PENDING = "pending"
    DRIFTED = "drifted"


@dataclass(frozen=True)
class MigrationStatusRow:
    version: int
    filename: str
    state: MigrationState
    checksum_file: str
    checksum_recorded: str | None
    applied_at: Any | None
    duration_ms: int | None


class DbConnection(Protocol):
    """Minimal connection protocol (psycopg Connection or test double)."""

    def execute(self, query: str, params: Any = None) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def cursor(self) -> Any: ...


@dataclass
class AppliedRow:
    version: int
    filename: str
    checksum: str
    applied_at: Any
    duration_ms: int


class MigrationRunner:
    def __init__(
        self,
        conn: DbConnection,
        migrations_dir: Path,
        *,
        migrations: list[MigrationFile] | None = None,
        lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.conn = conn
        self.migrations_dir = Path(migrations_dir)
        self.migrations = (
            migrations
            if migrations is not None
            else discover_migrations(self.migrations_dir)
        )
        self.lock_timeout_seconds = lock_timeout_seconds
        self._lock_held = False

    # --- locking -----------------------------------------------------------

    def acquire_lock(self) -> None:
        """Acquire session advisory lock before any mutating migration work.

        Waits up to ``lock_timeout_seconds``, then fails loudly.
        """
        if self._lock_held:
            return
        timeout_ms = max(1, int(self.lock_timeout_seconds * 1000))
        try:
            self.conn.execute(
                "SELECT set_config('lock_timeout', %s, false)",
                (str(timeout_ms),),
            )
            self.conn.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
            self.conn.commit()
            self._lock_held = True
        except Exception as exc:  # noqa: BLE001
            self.conn.rollback()
            raise MigrationLockError(
                f"could not acquire migration advisory lock "
                f"(key={ADVISORY_LOCK_KEY}) within {self.lock_timeout_seconds}s: {exc}"
            ) from exc

    def release_lock(self) -> None:
        if not self._lock_held:
            return
        try:
            self.conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))
            self.conn.commit()
        except Exception:  # noqa: BLE001 — disconnect also releases session locks
            self.conn.rollback()
        finally:
            self._lock_held = False

    # --- bootstrap ---------------------------------------------------------

    def ensure_tracking_table(self) -> None:
        """Create ``schema_migrations`` if missing (idempotent bootstrap)."""
        self.conn.execute(SCHEMA_MIGRATIONS_DDL)
        self.conn.commit()

    def tracking_table_exists(self) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname = 'public'
              AND c.relname = %s
            LIMIT 1
            """,
            (TRACKING_TABLE,),
        ).fetchone()
        return row is not None

    def current_database(self) -> str:
        row = self.conn.execute("SELECT current_database()").fetchone()
        return str(row[0]) if row else ""

    def non_system_user_object_count(self, *, exclude_tracking: bool = True) -> int:
        """Count tables/views/matviews/sequences/foreign tables in non-system schemas.

        Fail-closed legacy detection: ANY user object (any schema) means the DB
        is not a blank slate — even if ``public`` has no base tables.
        """
        sql = """
            SELECT COUNT(*)::int
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname <> ALL (%s)
              AND n.nspname !~ '^pg_(temp|toast_temp)_'
              AND c.relkind = ANY (%s)
        """
        schemas = list(_SYSTEM_SCHEMAS)
        relkinds = ["r", "p", "v", "m", "S", "f"]
        params: list[Any] = [schemas, relkinds]
        if exclude_tracking:
            sql += """
              AND NOT (n.nspname = 'public' AND c.relname = %s)
            """
            params.append(TRACKING_TABLE)
        row = self.conn.execute(sql, tuple(params)).fetchone()
        return int(row[0] if row else 0)

    # Back-compat alias used by older unit tests / CLI paths.
    def public_user_table_count(self, *, exclude_tracking: bool = True) -> int:
        return self.non_system_user_object_count(exclude_tracking=exclude_tracking)

    def is_unbaselined_legacy(self) -> bool:
        """True when user objects exist but tracking history is empty/missing.

        Production cutover: old SQL was applied by hand with no tracker. A
        normal ``apply`` must refuse rather than replay 001..N.
        """
        if not self.tracking_table_exists():
            return self.non_system_user_object_count(exclude_tracking=False) > 0

        applied = self._load_applied()
        if applied:
            return False
        return self.non_system_user_object_count(exclude_tracking=True) > 0

    # --- reads / history validation ----------------------------------------

    def _load_applied(self) -> dict[int, AppliedRow]:
        if not self.tracking_table_exists():
            return {}
        rows = self.conn.execute(
            """
            SELECT version, filename, checksum, applied_at, duration_ms
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
        out: dict[int, AppliedRow] = {}
        for row in rows:
            version = int(row[0])
            out[version] = AppliedRow(
                version=version,
                filename=str(row[1]),
                checksum=str(row[2]),
                applied_at=row[3],
                duration_ms=int(row[4]),
            )
        return out

    def validate_applied_history(
        self, applied: dict[int, AppliedRow] | None = None
    ) -> None:
        """Require nonempty history to be an exact contiguous prefix 001..N.

        Compares version, filename, and checksum against disk. Detects holes,
        non-prefix history (e.g. only 054), renamed files, missing files,
        rogue tracking rows, and checksum drift.
        """
        applied = self._load_applied() if applied is None else applied
        if not applied:
            return

        by_disk = {m.version: m for m in self.migrations}
        versions = sorted(applied.keys())
        problems: list[str] = []

        if versions[0] != 1:
            problems.append(
                f"history does not start at 001 (found high-water start {versions[0]:03d}); "
                f"a tracker containing only later versions must refuse apply"
            )

        expected = list(range(1, versions[-1] + 1))
        missing = [v for v in expected if v not in applied]
        if missing:
            preview = ", ".join(f"{v:03d}" for v in missing[:12])
            more = "" if len(missing) <= 12 else f" (+{len(missing) - 12} more)"
            problems.append(f"holes in tracking history: missing {preview}{more}")

        for version, rec in sorted(applied.items()):
            mig = by_disk.get(version)
            if mig is None:
                problems.append(
                    f"{version:03d} recorded as {rec.filename!r} but file is missing from disk"
                )
                continue
            if mig.filename != rec.filename:
                problems.append(
                    f"{version:03d} filename mismatch: recorded={rec.filename!r} "
                    f"disk={mig.filename!r}"
                )
            if mig.checksum != rec.checksum:
                problems.append(
                    f"{version:03d} ({mig.filename}): checksum drift "
                    f"recorded={rec.checksum} disk={mig.checksum}"
                )

        if problems:
            # Prefer ChecksumDriftError when every problem is checksum-only.
            if problems and all("checksum drift" in p for p in problems):
                raise ChecksumDriftError(
                    "checksum drift detected — migration history is immutable; "
                    "do not edit applied SQL files. Details:\n  - "
                    + "\n  - ".join(problems)
                )
            raise HistoryIntegrityError(
                "REFUSING: schema_migrations history is not a clean contiguous "
                "prefix 001..N matching disk (version+filename+checksum). Details:\n  - "
                + "\n  - ".join(problems)
            )

    def assert_no_checksum_drift(
        self, applied: dict[int, AppliedRow] | None = None
    ) -> None:
        """Alias kept for callers; full history validation is authoritative."""
        self.validate_applied_history(applied)

    def status_rows(self) -> list[MigrationStatusRow]:
        applied = self._load_applied() if self.tracking_table_exists() else {}
        # Always validate when tracker has rows so status --require-current
        # cannot pass on drift / holes / rogue history.
        if applied:
            self.validate_applied_history(applied)

        rows: list[MigrationStatusRow] = []
        for mig in self.migrations:
            rec = applied.get(mig.version)
            if rec is None:
                state = MigrationState.PENDING
                checksum_recorded = None
                applied_at = None
                duration_ms = None
            elif rec.checksum != mig.checksum or rec.filename != mig.filename:
                state = MigrationState.DRIFTED
                checksum_recorded = rec.checksum
                applied_at = rec.applied_at
                duration_ms = rec.duration_ms
            else:
                state = MigrationState.APPLIED
                checksum_recorded = rec.checksum
                applied_at = rec.applied_at
                duration_ms = rec.duration_ms
            rows.append(
                MigrationStatusRow(
                    version=mig.version,
                    filename=mig.filename,
                    state=state,
                    checksum_file=mig.checksum,
                    checksum_recorded=checksum_recorded,
                    applied_at=applied_at,
                    duration_ms=duration_ms,
                )
            )
        return rows

    # --- baseline / stamp --------------------------------------------------

    def baseline(
        self,
        *,
        through: int,
        confirm_baseline: int,
        expect_database: str,
    ) -> list[MigrationFile]:
        """Stamp migrations ``1..through`` without executing SQL.

        Initial baseline only — tracker must be empty. Never fills holes in
        partial history. Requires deliberate confirmation tokens that include
        the high-water mark and expected ``current_database()`` identity.
        Baseline is operator attestation of history; it does not inspect
        whether each historical DDL effect exists.
        """
        if through < 1:
            raise MigrationError("--through must be >= 1")
        if confirm_baseline != through:
            raise BaselineConfirmationError(
                f"--confirm-baseline ({confirm_baseline}) must exactly equal "
                f"--through ({through})"
            )
        expect = (expect_database or "").strip()
        if not expect:
            raise BaselineConfirmationError(
                "--expect-database is required (must match current_database())"
            )

        self.acquire_lock()
        try:
            actual_db = self.current_database()
            if actual_db != expect:
                raise BaselineConfirmationError(
                    f"--expect-database {expect!r} does not match server "
                    f"current_database()={actual_db!r}"
                )

            known = {m.version for m in self.migrations}
            if through not in known:
                raise MigrationError(
                    f"--through {through} does not match a migration file "
                    f"(have 1..{max(known) if known else 0})"
                )

            self.ensure_tracking_table()
            applied = self._load_applied()
            if applied:
                raise MigrationError(
                    "REFUSING BASELINE: schema_migrations is not empty. "
                    "Initial baseline is only allowed on an empty tracker. "
                    "Hole-filling / repair of partial history is not supported "
                    "by this command (requires an explicitly guarded repair path)."
                )

            stamped: list[MigrationFile] = []
            for mig in self.migrations:
                if mig.version > through:
                    break
                self._record(mig, duration_ms=0)
                stamped.append(mig)
            self.conn.commit()
            return stamped
        finally:
            self.release_lock()

    # --- apply -------------------------------------------------------------

    def apply(self) -> list[MigrationFile]:
        """Apply pending migrations in order. Stop on first failure.

        Acquires the advisory lock before bootstrap/history checks. Refuses
        unbaselined legacy databases and non-prefix tracking history. No-op
        when already current (after history validation).
        """
        self.acquire_lock()
        try:
            legacy_before = self.is_unbaselined_legacy()
            self.ensure_tracking_table()

            if legacy_before or self.is_unbaselined_legacy():
                raise BaselineRequiredError(
                    "REFUSING APPLY: this database has existing user objects "
                    "(tables/views/matviews/sequences in any non-system schema) "
                    "but no schema_migrations history. Replaying 001..N would be "
                    "unsafe. Inspect the high-water mark already applied by hand, "
                    "then run an explicit baseline (never implicit), e.g.:\n"
                    "  python -m src.db_migrations baseline --through 054 "
                    "--confirm-baseline 054 --expect-database <current_database()>\n"
                    "  python -m src.db_migrations status --require-current\n"
                    "See infra/db/README.md (production cutover)."
                )

            applied = self._load_applied()
            # Nonempty history must be exact prefix 001..N before applying N+1.
            # A tracker containing only 054 must refuse, not execute 001-053.
            self.validate_applied_history(applied)

            pending = [m for m in self.migrations if m.version not in applied]
            if not pending:
                return []

            applied_now: list[MigrationFile] = []
            for mig in pending:
                sql = mig.path.read_text(encoding="utf-8")
                started = time.perf_counter()
                try:
                    # Multi-statement / dollar-quoted files: full script via cursor.
                    with self.conn.cursor() as cur:
                        cur.execute(sql)
                    duration_ms = int(round((time.perf_counter() - started) * 1000))
                    self._record(mig, duration_ms=duration_ms)
                    self.conn.commit()
                except Exception as exc:  # noqa: BLE001 — surface then stop
                    self.conn.rollback()
                    raise MigrationApplyError(mig.version, mig.filename, exc) from exc
                applied_now.append(mig)
            return applied_now
        finally:
            self.release_lock()

    def _record(self, mig: MigrationFile, *, duration_ms: int) -> None:
        if duration_ms < 0:
            raise MigrationError("duration_ms must be nonnegative")
        self.conn.execute(
            """
            INSERT INTO schema_migrations (version, filename, checksum, duration_ms)
            VALUES (%s, %s, %s, %s)
            """,
            (mig.version, mig.filename, mig.checksum, duration_ms),
        )


def format_status(
    rows: list[MigrationStatusRow],
    *,
    unbaselined_legacy: bool = False,
) -> str:
    lines: list[str] = []
    if unbaselined_legacy:
        lines.append(
            "WARNING: unbaselined legacy database — apply will REFUSE until "
            "you run an explicit baseline/stamp with confirmation tokens."
        )
    if not rows:
        lines.append("(no migration files found)")
        return "\n".join(lines)

    width = max(len(r.filename) for r in rows)
    for r in rows:
        extra = ""
        if r.state is MigrationState.DRIFTED:
            extra = "  DRIFT (filename/checksum)"
        elif r.state is MigrationState.APPLIED and r.duration_ms is not None:
            extra = f"  ({r.duration_ms} ms)"
        lines.append(
            f"{r.version:03d}  {r.filename:<{width}}  {r.state.value}{extra}"
        )

    counts = {s: 0 for s in MigrationState}
    for r in rows:
        counts[r.state] += 1
    lines.append(
        f"-- applied={counts[MigrationState.APPLIED]} "
        f"pending={counts[MigrationState.PENDING]} "
        f"drifted={counts[MigrationState.DRIFTED]}"
    )
    return "\n".join(lines)
