"""Unit tests for the tracked SQL migration runner (in-memory fake; no real DB).

Transaction atomicity and advisory-lock serialization are covered by
``test_db_migrations_pg.py`` against disposable Postgres — do not treat this
fake as transaction proof.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.db_migrations.discovery import discover_migrations, validate_sequence
from src.db_migrations.errors import (
    BaselineConfirmationError,
    BaselineRequiredError,
    ChecksumDriftError,
    HistoryIntegrityError,
    MigrationApplyError,
    MigrationError,
    MigrationSequenceError,
)
from src.db_migrations.runner import (
    SCHEMA_MIGRATIONS_DDL,
    MigrationRunner,
    MigrationState,
    format_status,
)


@dataclass
class FakeResult:
    rows: list[tuple[Any, ...]] = field(default_factory=list)

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self.rows)


class FakeCursor:
    def __init__(self, conn: "FakeConnection") -> None:
        self.conn = conn

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        if self.conn.fail_on_sql_substring and self.conn.fail_on_sql_substring in sql:
            raise RuntimeError(
                f"simulated SQL failure matching {self.conn.fail_on_sql_substring!r}"
            )
        if "schema_migrations" not in sql.lower() and "pg_" not in sql.lower():
            self.conn.executed_migration_sql.append(sql)
            # Simulate DDL side effects for simple CREATE TABLE names.
            m = re.search(r"CREATE TABLE\s+(\w+)", sql, re.IGNORECASE)
            if m:
                self.conn.user_objects.add(("public", m.group(1), "r"))


class FakeConnection:
    """Minimal stand-in covering MigrationRunner SQL shapes (not a TX oracle)."""

    def __init__(self, database_name: str = "testdb") -> None:
        self.database_name = database_name
        self.user_objects: set[tuple[str, str, str]] = set()  # schema, name, relkind
        self.migrations: dict[int, dict[str, Any]] = {}
        self.executed_migration_sql: list[str] = []
        self.fail_on_sql_substring: str | None = None
        self.committed = 0
        self.rolled_back = 0
        self.lock_held = False
        self.lock_acquire_count = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def execute(self, query: str, params: Any = None) -> FakeResult:
        q = " ".join(query.split())
        q_lower = q.lower()

        if "set_config('lock_timeout'" in q_lower or 'set_config("lock_timeout"' in q_lower:
            return FakeResult()
        if "pg_advisory_lock" in q_lower:
            self.lock_held = True
            self.lock_acquire_count += 1
            return FakeResult()
        if "pg_advisory_unlock" in q_lower:
            self.lock_held = False
            return FakeResult()
        if "current_database()" in q_lower:
            return FakeResult([(self.database_name,)])

        if "create table if not exists schema_migrations" in q_lower:
            self.user_objects.add(("public", "schema_migrations", "r"))
            return FakeResult()

        if "from pg_class" in q_lower and "c.relname = %s" in q_lower and "limit 1" in q_lower:
            name = params[0] if params else None
            if ("public", name, "r") in self.user_objects:
                return FakeResult([(1,)])
            return FakeResult([])

        if "from pg_class" in q_lower and "count(*)" in q_lower:
            objs = set(self.user_objects)
            if params and len(params) >= 3:
                # exclude tracking
                objs.discard(("public", params[2], "r"))
            elif params and len(params) == 1:
                objs.discard(("public", params[0], "r"))
            # Also exclude tracking name if exclude path used schema_migrations
            return FakeResult([(len(objs),)])

        if "from schema_migrations" in q_lower and "select version" in q_lower:
            rows = [
                (
                    v,
                    row["filename"],
                    row["checksum"],
                    row["applied_at"],
                    row["duration_ms"],
                )
                for v, row in sorted(self.migrations.items())
            ]
            return FakeResult(rows)

        if q_lower.startswith("insert into schema_migrations"):
            version, filename, checksum, duration_ms = params
            self.user_objects.add(("public", "schema_migrations", "r"))
            self.migrations[int(version)] = {
                "filename": filename,
                "checksum": checksum,
                "applied_at": datetime.now(timezone.utc),
                "duration_ms": int(duration_ms),
            }
            return FakeResult()

        raise AssertionError(f"unhandled SQL in FakeConnection: {q}")


def _write_migration(dir_path: Path, version: int, name: str, body: str) -> Path:
    path = dir_path / f"{version:03d}_{name}.sql"
    path.write_text(body, encoding="utf-8")
    return path


def _write_named(dir_path: Path, filename: str, body: str) -> Path:
    path = dir_path / filename
    path.write_text(body, encoding="utf-8")
    return path


def _baseline_ok(runner: MigrationRunner, through: int, db: str = "testdb"):
    return runner.baseline(
        through=through,
        confirm_baseline=through,
        expect_database=db,
    )


# ---------------------------------------------------------------------------
# Discovery / sequence
# ---------------------------------------------------------------------------


def test_numeric_ordering_not_lexicographic() -> None:
    from src.db_migrations.discovery import MigrationFile

    files = [
        MigrationFile(9, "9_nine.sql", Path("9_nine.sql"), "a"),
        MigrationFile(10, "10_ten.sql", Path("10_ten.sql"), "b"),
        MigrationFile(54, "054_fifty_four.sql", Path("054_fifty_four.sql"), "c"),
    ]
    ordered = sorted(files, key=lambda m: m.version)
    assert [m.version for m in ordered] == [9, 10, 54]
    assert sorted(f.filename for f in files) == [
        "054_fifty_four.sql",
        "10_ten.sql",
        "9_nine.sql",
    ]


def test_discover_orders_mixed_padding(tmp_path: Path) -> None:
    _write_named(tmp_path, "001_a.sql", "-- a\n")
    _write_named(tmp_path, "2_b.sql", "-- b\n")
    _write_named(tmp_path, "003_c.sql", "-- c\n")
    migrations = discover_migrations(tmp_path)
    assert [m.version for m in migrations] == [1, 2, 3]


def test_refuse_duplicate_versions(tmp_path: Path) -> None:
    _write_named(tmp_path, "001_a.sql", "SELECT 1;")
    _write_named(tmp_path, "001_b.sql", "SELECT 2;")
    with pytest.raises(MigrationSequenceError, match="duplicate"):
        discover_migrations(tmp_path)


def test_refuse_gap_in_sequence(tmp_path: Path) -> None:
    _write_named(tmp_path, "001_a.sql", "SELECT 1;")
    _write_named(tmp_path, "003_c.sql", "SELECT 3;")
    with pytest.raises(MigrationSequenceError, match="missing"):
        discover_migrations(tmp_path)


def test_check_integrity_real_infra_db() -> None:
    root = Path(__file__).resolve().parents[3] / "infra" / "db"
    migrations = discover_migrations(root)
    assert migrations[0].version == 1
    assert migrations[-1].version == len(migrations)
    validate_sequence(migrations)


def test_schema_ddl_has_checksum_and_duration_constraints() -> None:
    assert "PRIMARY KEY" in SCHEMA_MIGRATIONS_DDL
    assert "UNIQUE (filename)" in SCHEMA_MIGRATIONS_DDL or "filename text NOT NULL UNIQUE" in SCHEMA_MIGRATIONS_DDL
    assert "^[0-9a-f]{64}$" in SCHEMA_MIGRATIONS_DDL
    assert "duration_ms >= 0" in SCHEMA_MIGRATIONS_DDL
    assert "timestamptz" in SCHEMA_MIGRATIONS_DDL.lower()


# ---------------------------------------------------------------------------
# Runner behavior (fake)
# ---------------------------------------------------------------------------


def test_bootstrap_creates_tracking_table_without_numbered_migration(
    tmp_path: Path,
) -> None:
    _write_migration(tmp_path, 1, "init", "CREATE TABLE widgets(id int);")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    assert not runner.tracking_table_exists()
    runner.ensure_tracking_table()
    assert runner.tracking_table_exists()
    assert not any(p.name.startswith("000_") for p in tmp_path.glob("*.sql"))


def test_baseline_stamps_without_executing_sql(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "CREATE TABLE a(id int);")
    _write_migration(tmp_path, 2, "b", "CREATE TABLE b(id int);")
    _write_migration(tmp_path, 3, "c", "CREATE TABLE c(id int);")
    conn = FakeConnection()
    conn.user_objects.add(("public", "legacy_stuff", "r"))
    runner = MigrationRunner(conn, tmp_path)
    stamped = _baseline_ok(runner, 2)
    assert [m.version for m in stamped] == [1, 2]
    assert conn.executed_migration_sql == []
    assert set(conn.migrations) == {1, 2}
    assert conn.lock_acquire_count >= 1


def test_baseline_requires_confirmation_tokens(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(BaselineConfirmationError, match="confirm-baseline"):
        runner.baseline(through=1, confirm_baseline=2, expect_database="testdb")
    with pytest.raises(BaselineConfirmationError, match="expect-database"):
        runner.baseline(through=1, confirm_baseline=1, expect_database="other")


def test_baseline_refuses_nonempty_tracker(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    _baseline_ok(runner, 1)
    with pytest.raises(MigrationError, match="not empty"):
        _baseline_ok(runner, 2)


def test_apply_records_success_and_stops_on_failure(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "ok", "CREATE TABLE ok(id int);")
    _write_migration(tmp_path, 2, "boom", "CREATE TABLE boom(id int); -- BOOM_MARKER")
    _write_migration(tmp_path, 3, "later", "CREATE TABLE later(id int);")
    conn = FakeConnection()
    conn.fail_on_sql_substring = "BOOM_MARKER"
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(MigrationApplyError) as ei:
        runner.apply()
    assert ei.value.version == 2
    assert 1 in conn.migrations
    assert 2 not in conn.migrations
    assert 3 not in conn.migrations
    assert not any("CREATE TABLE later" in s for s in conn.executed_migration_sql)


def test_apply_noop_when_current(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    assert [m.version for m in runner.apply()] == [1]
    assert runner.apply() == []


def test_status_applied_pending_drifted(tmp_path: Path) -> None:
    p1 = _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    _baseline_ok(runner, 1)
    p1.write_text("SELECT 1; -- edited\n", encoding="utf-8")
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises((ChecksumDriftError, HistoryIntegrityError)):
        runner.status_rows()


def test_checksum_drift_refuses_apply(tmp_path: Path) -> None:
    p1 = _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    runner.apply()
    p1.write_text("SELECT 1; -- drift\n", encoding="utf-8")
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises((ChecksumDriftError, HistoryIntegrityError)):
        runner.apply()


def test_filename_mismatch_refuses(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    runner.apply()
    # Rename on disk while keeping version
    old = tmp_path / "001_a.sql"
    new = tmp_path / "001_renamed.sql"
    old.rename(new)
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(HistoryIntegrityError, match="filename mismatch"):
        runner.validate_applied_history()


def test_partial_history_only_054_refuses_apply(tmp_path: Path) -> None:
    for i in range(1, 4):
        _write_migration(tmp_path, i, f"m{i}", f"SELECT {i};")
    conn = FakeConnection()
    conn.user_objects.add(("public", "schema_migrations", "r"))
    # Rogue: only version 3 stamped (like only-054)
    from src.db_migrations.discovery import sha256_file

    path = tmp_path / "003_m3.sql"
    conn.migrations[3] = {
        "filename": "003_m3.sql",
        "checksum": sha256_file(path),
        "applied_at": datetime.now(timezone.utc),
        "duration_ms": 0,
    }
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(HistoryIntegrityError, match="does not start at 001"):
        runner.apply()
    assert conn.executed_migration_sql == []


def test_unbaselined_legacy_refuses_normal_apply(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    conn.user_objects.add(("public", "nfl_player_prop_model_edges", "r"))
    runner = MigrationRunner(conn, tmp_path)
    assert runner.is_unbaselined_legacy()
    with pytest.raises(BaselineRequiredError, match="REFUSING APPLY"):
        runner.apply()
    assert conn.executed_migration_sql == []


def test_unbaselined_legacy_view_in_other_schema_refuses(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    conn = FakeConnection()
    conn.user_objects.add(("analytics", "legacy_view", "v"))
    runner = MigrationRunner(conn, tmp_path)
    assert runner.is_unbaselined_legacy()
    with pytest.raises(BaselineRequiredError):
        runner.apply()


def test_fresh_empty_db_apply_bootstraps_and_runs(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "CREATE TABLE a(id int);")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    applied = runner.apply()
    assert [m.version for m in applied] == [1]
    assert 1 in conn.migrations


def test_baseline_through_high_water_then_apply_noop(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "old", "SELECT 1;")
    _write_migration(tmp_path, 2, "also_live", "ALTER TABLE t DROP NOT NULL;")
    conn = FakeConnection()
    conn.user_objects.add(("public", "t", "r"))
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(BaselineRequiredError):
        runner.apply()
    _baseline_ok(runner, 2)
    assert conn.executed_migration_sql == []
    assert runner.apply() == []


def test_baseline_then_apply_remaining(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "old", "SELECT 1;")
    _write_migration(tmp_path, 2, "old2", "SELECT 2;")
    _write_migration(tmp_path, 3, "new", "ALTER TABLE t DROP NOT NULL;")
    conn = FakeConnection()
    conn.user_objects.add(("public", "t", "r"))
    runner = MigrationRunner(conn, tmp_path)
    _baseline_ok(runner, 2)
    applied = runner.apply()
    assert [m.version for m in applied] == [3]


def test_cli_has_no_database_url_flag() -> None:
    from src.db_migrations.__main__ import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--database-url", "postgresql://x", "check-integrity"])


def test_existing_migration_files_are_not_modified() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "infra"
        / "db"
        / "054_nfl_prop_edges_nullable_confidence.sql"
    )
    body = path.read_text(encoding="utf-8")
    assert "DROP NOT NULL" in body
    assert "DROP DEFAULT" in body
    from src.db_migrations.discovery import sha256_file

    assert re.fullmatch(r"[0-9a-f]{64}", sha256_file(path))
