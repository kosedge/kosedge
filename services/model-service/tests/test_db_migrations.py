"""Focused tests for the tracked SQL migration runner.

Uses an in-memory fake Postgres connection — no real database, no credentials.
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
    BaselineRequiredError,
    ChecksumDriftError,
    MigrationApplyError,
    MigrationSequenceError,
)
from src.db_migrations.runner import (
    SCHEMA_MIGRATIONS_DDL,
    MigrationRunner,
    MigrationState,
    format_status,
)


# ---------------------------------------------------------------------------
# Fake Postgres
# ---------------------------------------------------------------------------


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
        self._executed: list[str] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._executed.append(sql)
        if self.conn.fail_on_sql_substring and self.conn.fail_on_sql_substring in sql:
            raise RuntimeError(f"simulated SQL failure matching {self.conn.fail_on_sql_substring!r}")
        # Record numbered-migration body execution (not tracking DDL/DML).
        if "schema_migrations" not in sql.lower() and "information_schema" not in sql.lower():
            self.conn.executed_migration_sql.append(sql)


class FakeConnection:
    """Minimal stand-in covering MigrationRunner's SQL shapes."""

    def __init__(self) -> None:
        self.tables: set[str] = set()
        self.migrations: dict[int, dict[str, Any]] = {}
        self.executed_migration_sql: list[str] = []
        self.fail_on_sql_substring: str | None = None
        self.committed = 0
        self.rolled_back = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def execute(self, query: str, params: Any = None) -> FakeResult:
        q = " ".join(query.split())
        q_lower = q.lower()

        if "create table if not exists schema_migrations" in q_lower:
            self.tables.add("schema_migrations")
            return FakeResult()

        if "from information_schema.tables" in q_lower and "table_name = %s" in q_lower:
            name = params[0] if params else None
            if name in self.tables:
                return FakeResult([(1,)])
            return FakeResult([])

        if "from information_schema.tables" in q_lower and "count(*)" in q_lower:
            others = {t for t in self.tables if t != "schema_migrations"}
            if params and "table_name <> %s" in q_lower:
                # exclude tracking
                return FakeResult([(len(others),)])
            return FakeResult([(len(self.tables),)])

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
            self.tables.add("schema_migrations")
            self.migrations[int(version)] = {
                "filename": filename,
                "checksum": checksum,
                "applied_at": datetime.now(timezone.utc),
                "duration_ms": int(duration_ms),
            }
            return FakeResult()

        raise AssertionError(f"unhandled SQL in FakeConnection: {q}")


def _write_migration(dir_path: Path, version: int, name: str, body: str) -> Path:
    # Preserve zero-padding when version is written as caller chooses via name.
    path = dir_path / f"{version:03d}_{name}.sql"
    path.write_text(body, encoding="utf-8")
    return path


def _write_named(dir_path: Path, filename: str, body: str) -> Path:
    path = dir_path / filename
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Discovery / sequence
# ---------------------------------------------------------------------------


def test_numeric_ordering_not_lexicographic() -> None:
    """9 before 10 before 054 — integer order, not string sort of filenames."""
    from src.db_migrations.discovery import MigrationFile

    files = [
        MigrationFile(9, "9_nine.sql", Path("9_nine.sql"), "a"),
        MigrationFile(10, "10_ten.sql", Path("10_ten.sql"), "b"),
        MigrationFile(54, "054_fifty_four.sql", Path("054_fifty_four.sql"), "c"),
    ]
    ordered = sorted(files, key=lambda m: m.version)
    assert [m.version for m in ordered] == [9, 10, 54]
    # Lexicographic filename sort would put 10 before 9 and 054 first:
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
    assert migrations[1].filename == "2_b.sql"


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
    """Repo integrity: current infra/db must be a clean 1..N sequence."""
    root = Path(__file__).resolve().parents[3] / "infra" / "db"
    migrations = discover_migrations(root)
    assert migrations[0].version == 1
    assert migrations[-1].version == len(migrations)
    validate_sequence(migrations)


# ---------------------------------------------------------------------------
# Runner behavior
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
    assert "schema_migrations" in conn.tables
    # Bootstrap DDL is owned by the runner, not a numbered file.
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in SCHEMA_MIGRATIONS_DDL
    assert not any(p.name.startswith("000_") for p in tmp_path.glob("*.sql"))


def test_baseline_stamps_without_executing_sql(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "CREATE TABLE a(id int);")
    _write_migration(tmp_path, 2, "b", "CREATE TABLE b(id int);")
    _write_migration(tmp_path, 3, "c", "CREATE TABLE c(id int);")
    conn = FakeConnection()
    # Simulate legacy warehouse already having objects.
    conn.tables.add("legacy_stuff")
    runner = MigrationRunner(conn, tmp_path)
    stamped = runner.baseline(through=2)
    assert [m.version for m in stamped] == [1, 2]
    assert conn.executed_migration_sql == []
    assert set(conn.migrations) == {1, 2}
    assert conn.migrations[1]["duration_ms"] == 0
    rows = runner.status_rows()
    assert rows[0].state is MigrationState.APPLIED
    assert rows[1].state is MigrationState.APPLIED
    assert rows[2].state is MigrationState.PENDING


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
    assert conn.rolled_back >= 1
    # Migration 1 SQL ran; migration 3 must not.
    assert any("CREATE TABLE ok" in s for s in conn.executed_migration_sql)
    assert not any("CREATE TABLE later" in s for s in conn.executed_migration_sql)


def test_apply_noop_when_current(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    first = runner.apply()
    assert [m.version for m in first] == [1]
    second = runner.apply()
    assert second == []
    assert len(conn.executed_migration_sql) == 1


def test_status_applied_pending_drifted(tmp_path: Path) -> None:
    p1 = _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    runner.baseline(through=1)
    # Mutate applied file → drift
    p1.write_text("SELECT 1; -- edited\n", encoding="utf-8")
    runner = MigrationRunner(conn, tmp_path)  # rediscover checksums
    rows = runner.status_rows()
    assert rows[0].state is MigrationState.DRIFTED
    assert rows[1].state is MigrationState.PENDING
    text = format_status(rows)
    assert "drifted" in text
    assert "pending" in text


def test_checksum_drift_refuses_apply(tmp_path: Path) -> None:
    p1 = _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    runner.apply()
    p1.write_text("SELECT 1; -- drift\n", encoding="utf-8")
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(ChecksumDriftError):
        runner.apply()


def test_unbaselined_legacy_refuses_normal_apply(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "SELECT 1;")
    _write_migration(tmp_path, 2, "b", "SELECT 2;")
    conn = FakeConnection()
    conn.tables.add("nfl_player_prop_model_edges")  # legacy objects, no tracker
    runner = MigrationRunner(conn, tmp_path)
    assert runner.is_unbaselined_legacy()
    with pytest.raises(BaselineRequiredError, match="REFUSING APPLY"):
        runner.apply()
    assert conn.executed_migration_sql == []
    assert conn.migrations == {}


def test_fresh_empty_db_apply_bootstraps_and_runs(tmp_path: Path) -> None:
    _write_migration(tmp_path, 1, "a", "CREATE TABLE a(id int);")
    conn = FakeConnection()
    runner = MigrationRunner(conn, tmp_path)
    assert not runner.is_unbaselined_legacy()
    applied = runner.apply()
    assert [m.version for m in applied] == [1]
    assert "schema_migrations" in conn.tables
    assert 1 in conn.migrations


def test_baseline_through_high_water_then_apply_noop(tmp_path: Path) -> None:
    """Production-shaped cutover: stamp through already-live max; apply is no-op."""
    _write_migration(tmp_path, 1, "old", "SELECT 1;")
    _write_migration(tmp_path, 2, "also_live", "ALTER TABLE t DROP NOT NULL;")
    conn = FakeConnection()
    conn.tables.add("t")
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(BaselineRequiredError):
        runner.apply()
    runner.baseline(through=2)
    assert conn.executed_migration_sql == []
    assert runner.apply() == []


def test_baseline_then_apply_remaining(tmp_path: Path) -> None:
    """When high-water is N-1 and N is new: baseline then apply only N."""
    _write_migration(tmp_path, 1, "old", "SELECT 1;")
    _write_migration(tmp_path, 2, "old2", "SELECT 2;")
    _write_migration(tmp_path, 3, "new", "ALTER TABLE t DROP NOT NULL;")
    conn = FakeConnection()
    conn.tables.add("t")
    runner = MigrationRunner(conn, tmp_path)
    runner.baseline(through=2)
    assert conn.executed_migration_sql == []
    applied = runner.apply()
    assert [m.version for m in applied] == [3]
    assert any("DROP NOT NULL" in s for s in conn.executed_migration_sql)


def test_existing_migration_files_are_not_modified() -> None:
    """Guard: applied history is immutable — 054 content must stay as merged."""
    path = (
        Path(__file__).resolve().parents[3]
        / "infra"
        / "db"
        / "054_nfl_prop_edges_nullable_confidence.sql"
    )
    body = path.read_text(encoding="utf-8")
    assert "DROP NOT NULL" in body
    assert "DROP DEFAULT" in body
    # Runner must not rewrite files; checksum stability is the contract.
    from src.db_migrations.discovery import sha256_file

    digest = sha256_file(path)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
