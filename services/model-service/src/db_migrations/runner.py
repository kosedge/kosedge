"""Apply / baseline / status for numbered SQL migrations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .discovery import MigrationFile, discover_migrations
from .errors import (
    BaselineRequiredError,
    ChecksumDriftError,
    MigrationApplyError,
    MigrationError,
)

# Bootstrap is deliberate and NOT a numbered migration. The runner requires this
# table before it can track anything; creating it via 055-style SQL would nest a
# chicken-and-egg dependency on the tracker itself.
SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version integer PRIMARY KEY,
  filename text NOT NULL UNIQUE,
  checksum text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now(),
  duration_ms integer NOT NULL
);
""".strip()

TRACKING_TABLE = "schema_migrations"


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
    ) -> None:
        self.conn = conn
        self.migrations_dir = Path(migrations_dir)
        self.migrations = migrations if migrations is not None else discover_migrations(
            self.migrations_dir
        )

    # --- bootstrap ---------------------------------------------------------

    def ensure_tracking_table(self) -> None:
        """Create ``schema_migrations`` if missing (idempotent bootstrap)."""
        self.conn.execute(SCHEMA_MIGRATIONS_DDL)
        self.conn.commit()

    def tracking_table_exists(self) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
            LIMIT 1
            """,
            (TRACKING_TABLE,),
        ).fetchone()
        return row is not None

    def public_user_table_count(self, *, exclude_tracking: bool = True) -> int:
        if exclude_tracking:
            row = self.conn.execute(
                """
                SELECT COUNT(*)::int
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                  AND table_name <> %s
                """,
                (TRACKING_TABLE,),
            ).fetchone()
        else:
            row = self.conn.execute(
                """
                SELECT COUNT(*)::int
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            ).fetchone()
        return int(row[0] if row else 0)

    def is_unbaselined_legacy(self) -> bool:
        """True when the DB looks populated but has no migration tracking rows.

        Production cutover: old SQL was applied by hand with no tracker. A
        normal ``apply`` must refuse rather than replay 001..N.
        """
        if not self.tracking_table_exists():
            return self.public_user_table_count(exclude_tracking=False) > 0

        applied = self._load_applied()
        if applied:
            return False
        return self.public_user_table_count(exclude_tracking=True) > 0

    # --- reads -------------------------------------------------------------

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

    def status_rows(self) -> list[MigrationStatusRow]:
        applied = self._load_applied() if self.tracking_table_exists() else {}
        rows: list[MigrationStatusRow] = []
        for mig in self.migrations:
            rec = applied.get(mig.version)
            if rec is None:
                state = MigrationState.PENDING
                checksum_recorded = None
                applied_at = None
                duration_ms = None
            elif rec.checksum != mig.checksum:
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

    def assert_no_checksum_drift(self, applied: dict[int, AppliedRow] | None = None) -> None:
        applied = self._load_applied() if applied is None else applied
        by_version = {m.version: m for m in self.migrations}
        drifted: list[str] = []
        for version, rec in sorted(applied.items()):
            mig = by_version.get(version)
            if mig is None:
                drifted.append(
                    f"{version:03d} recorded as {rec.filename} but file is missing from disk"
                )
                continue
            if mig.checksum != rec.checksum:
                drifted.append(
                    f"{version:03d} ({mig.filename}): recorded={rec.checksum} file={mig.checksum}"
                )
        if drifted:
            raise ChecksumDriftError(
                "checksum drift detected — migration history is immutable; "
                "do not edit applied SQL files. Details:\n  - "
                + "\n  - ".join(drifted)
            )

    # --- baseline / stamp --------------------------------------------------

    def baseline(self, *, through: int) -> list[MigrationFile]:
        """Stamp migrations ``<= through`` without executing SQL.

        Never called implicitly by ``apply``.
        """
        if through < 1:
            raise MigrationError("--through must be >= 1")

        known = {m.version for m in self.migrations}
        if through not in known:
            raise MigrationError(
                f"--through {through} does not match a migration file "
                f"(have 1..{max(known) if known else 0})"
            )

        self.ensure_tracking_table()
        applied = self._load_applied()
        self.assert_no_checksum_drift(applied)

        stamped: list[MigrationFile] = []
        for mig in self.migrations:
            if mig.version > through:
                break
            if mig.version in applied:
                continue
            self._record(mig, duration_ms=0)
            stamped.append(mig)
        self.conn.commit()
        return stamped

    # --- apply -------------------------------------------------------------

    def apply(self) -> list[MigrationFile]:
        """Apply pending migrations in order. Stop on first failure.

        Refuses unbaselined legacy databases. No-op when already current
        (after drift checks).
        """
        # Bootstrap first so empty DBs can start cleanly. Legacy safety still
        # inspects other user tables / existing tracking rows.
        legacy_before = self.is_unbaselined_legacy()
        self.ensure_tracking_table()

        if legacy_before or self.is_unbaselined_legacy():
            raise BaselineRequiredError(
                "REFUSING APPLY: this database has existing public tables but "
                "no schema_migrations history. Replaying 001..N would be unsafe. "
                "Inspect the high-water mark of SQL already applied by hand, then "
                "run an explicit baseline/stamp (never implicit), e.g.:\n"
                "  python -m src.db_migrations baseline --through 054\n"
                "  python -m src.db_migrations status --require-current\n"
                "See infra/db/README.md (production cutover)."
            )

        applied = self._load_applied()
        self.assert_no_checksum_drift(applied)

        pending = [m for m in self.migrations if m.version not in applied]
        if not pending:
            return []

        applied_now: list[MigrationFile] = []
        for mig in pending:
            sql = mig.path.read_text(encoding="utf-8")
            started = time.perf_counter()
            try:
                # Multi-statement files: use a cursor execute of the full script.
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

    def _record(self, mig: MigrationFile, *, duration_ms: int) -> None:
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
            "you run an explicit baseline/stamp."
        )
    if not rows:
        lines.append("(no migration files found)")
        return "\n".join(lines)

    width = max(len(r.filename) for r in rows)
    for r in rows:
        extra = ""
        if r.state is MigrationState.DRIFTED:
            extra = "  CHECKSUM DRIFT"
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
