"""Real-Postgres integration tests for the migration runner.

Requires ``MIG_TEST_DATABASE_URL`` (preferred) or a reachable ``DATABASE_URL``.
Skipped automatically when Postgres is unavailable — CI must provide a service
container. These tests prove transaction/lock semantics the in-memory fake cannot.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

from src.db_migrations.errors import (  # noqa: E402
    BaselineRequiredError,
    HistoryIntegrityError,
    MigrationApplyError,
    MigrationLockError,
)
from src.db_migrations.paths import normalize_database_url  # noqa: E402
from src.db_migrations.runner import (  # noqa: E402
    ADVISORY_LOCK_KEY,
    MigrationRunner,
    SCHEMA_MIGRATIONS_DDL,
)


def _integration_url() -> str | None:
    raw = (
        os.environ.get("MIG_TEST_DATABASE_URL")
        or os.environ.get("KOSEDGE_MIG_TEST_DATABASE_URL")
        or ""
    ).strip()
    if not raw:
        # Only fall back to DATABASE_URL when it looks like a local test DSN
        # (avoid accidentally hitting a real warehouse URL in agent envs).
        candidate = (os.environ.get("DATABASE_URL") or "").strip()
        if any(h in candidate for h in ("localhost", "127.0.0.1", "@postgres:")):
            raw = candidate
    if not raw:
        return None
    return normalize_database_url(raw)


def _can_connect(url: str) -> bool:
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


INTEGRATION_URL = _integration_url()
pytestmark = pytest.mark.skipif(
    not INTEGRATION_URL or not _can_connect(INTEGRATION_URL),
    reason="MIG_TEST_DATABASE_URL / local Postgres not available",
)


@pytest.fixture()
def pg_conn():
    assert INTEGRATION_URL
    conn = psycopg.connect(INTEGRATION_URL)
    conn.execute("SELECT pg_advisory_unlock_all()")
    # Isolate each test in a disposable schema + wipe public tracker leftovers.
    schema = f"migtest_{uuid.uuid4().hex[:12]}"
    conn.execute(f'CREATE SCHEMA "{schema}"')
    conn.execute("DROP TABLE IF EXISTS public.schema_migrations CASCADE")
    # Drop leftover public objects from prior tests (best-effort).
    conn.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN
            SELECT c.relname, c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind IN ('r','v','m','S','p')
              AND c.relname <> 'schema_migrations'
          LOOP
            IF r.relkind = 'S' THEN
              EXECUTE format('DROP SEQUENCE IF EXISTS public.%I CASCADE', r.relname);
            ELSIF r.relkind IN ('v','m') THEN
              EXECUTE format('DROP VIEW IF EXISTS public.%I CASCADE', r.relname);
            ELSE
              EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', r.relname);
            END IF;
          END LOOP;
        END $$;
        """
    )
    conn.commit()
    try:
        yield conn, schema
    finally:
        conn.rollback()
        try:
            conn.execute("SELECT pg_advisory_unlock_all()")
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            conn.execute("DROP TABLE IF EXISTS public.schema_migrations CASCADE")
            conn.commit()
        except Exception:  # noqa: BLE001
            conn.rollback()
        conn.close()


def _write(dir_path: Path, version: int, name: str, body: str) -> Path:
    path = dir_path / f"{version:03d}_{name}.sql"
    path.write_text(body, encoding="utf-8")
    return path


def test_schema_migrations_ddl_constraints(pg_conn) -> None:
    conn, _ = pg_conn
    conn.execute(SCHEMA_MIGRATIONS_DDL)
    conn.commit()
    # Bad checksum shape rejected.
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO schema_migrations (version, filename, checksum, duration_ms) "
            "VALUES (1, '001_x.sql', 'not-a-sha', 0)"
        )
        conn.commit()
    conn.rollback()
    # Negative duration rejected.
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO schema_migrations (version, filename, checksum, duration_ms) "
            "VALUES (1, '001_x.sql', %s, -1)",
            ("a" * 64,),
        )
        conn.commit()
    conn.rollback()


def test_apply_commits_ddl_and_tracking_atomically(pg_conn, tmp_path: Path) -> None:
    conn, _ = pg_conn
    _write(tmp_path, 1, "widgets", "CREATE TABLE widgets (id int PRIMARY KEY);")
    runner = MigrationRunner(conn, tmp_path)
    applied = runner.apply()
    assert [m.version for m in applied] == [1]
    assert conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='widgets'"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT version, filename FROM schema_migrations"
    ).fetchone() == (1, "001_widgets.sql")


def test_failing_migration_rolls_back_ddl_and_leaves_no_tracking_row(
    pg_conn, tmp_path: Path
) -> None:
    conn, _ = pg_conn
    _write(
        tmp_path,
        1,
        "partial",
        """
        CREATE TABLE keep_me_if_committed (id int);
        DO $$ BEGIN RAISE EXCEPTION 'boom_in_migration'; END $$;
        CREATE TABLE never_created (id int);
        """,
    )
    _write(tmp_path, 2, "later", "CREATE TABLE later_tbl (id int);")
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(MigrationApplyError) as ei:
        runner.apply()
    assert ei.value.version == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='keep_me_if_committed'"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='later_tbl'"
    ).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0


def test_dollar_quoted_and_multi_statement_sql(pg_conn, tmp_path: Path) -> None:
    conn, _ = pg_conn
    _write(
        tmp_path,
        1,
        "dollar",
        """
        CREATE TABLE dollar_demo (id int, note text);
        CREATE OR REPLACE FUNCTION dollar_demo_note() RETURNS text AS $fn$
        BEGIN
          RETURN 'ok';
        END;
        $fn$ LANGUAGE plpgsql;
        INSERT INTO dollar_demo (id, note) VALUES (1, dollar_demo_note());
        """,
    )
    runner = MigrationRunner(conn, tmp_path)
    runner.apply()
    note = conn.execute("SELECT note FROM dollar_demo").fetchone()[0]
    assert note == "ok"


def test_advisory_lock_serializes_two_concurrent_runners(pg_conn, tmp_path: Path) -> None:
    assert INTEGRATION_URL
    _write(
        tmp_path,
        1,
        "once",
        """
        CREATE TABLE IF NOT EXISTS once_tbl (id int);
        INSERT INTO once_tbl (id) VALUES (1);
        SELECT pg_sleep(1.5);
        """,
    )

    results: list[str] = []
    errors: list[BaseException] = []

    def worker(label: str) -> None:
        try:
            with psycopg.connect(INTEGRATION_URL) as c:
                # Ensure clean slate visibility; first worker creates.
                runner = MigrationRunner(c, tmp_path, lock_timeout_seconds=10)
                applied = runner.apply()
                results.append(f"{label}:{len(applied)}")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    # Pre-clean tracking / table from any prior attempt on this DB.
    with psycopg.connect(INTEGRATION_URL) as setup:
        setup.execute("DROP TABLE IF EXISTS once_tbl CASCADE")
        setup.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
        setup.execute("SELECT pg_advisory_unlock_all()")
        setup.commit()

    t1 = threading.Thread(target=worker, args=("a",))
    t2 = threading.Thread(target=worker, args=("b",))
    t1.start()
    time.sleep(0.2)
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    assert not errors, f"unexpected errors: {errors!r}"
    # One runner applies (1), the other sees current (0).
    assert sorted(results) == ["a:1", "b:0"] or sorted(results) == ["a:0", "b:1"]

    with psycopg.connect(INTEGRATION_URL) as check:
        count = check.execute("SELECT COUNT(*) FROM once_tbl").fetchone()[0]
        tracked = check.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert count == 1
        assert tracked == 1


def test_lock_timeout_fails_loudly(pg_conn, tmp_path: Path) -> None:
    assert INTEGRATION_URL
    _write(tmp_path, 1, "x", "CREATE TABLE lock_timeout_demo (id int);")
    blocker = psycopg.connect(INTEGRATION_URL)
    blocker.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
    blocker.commit()
    try:
        with psycopg.connect(INTEGRATION_URL) as c:
            runner = MigrationRunner(c, tmp_path, lock_timeout_seconds=1)
            with pytest.raises(MigrationLockError):
                runner.apply()
    finally:
        blocker.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))
        blocker.commit()
        blocker.close()


def test_partial_history_refuses_apply(pg_conn, tmp_path: Path) -> None:
    conn, _ = pg_conn
    for i in range(1, 4):
        _write(tmp_path, i, f"m{i}", f"SELECT {i};")
    conn.execute(SCHEMA_MIGRATIONS_DDL)
    from src.db_migrations.discovery import sha256_file

    path = tmp_path / "003_m3.sql"
    conn.execute(
        "INSERT INTO schema_migrations (version, filename, checksum, duration_ms) "
        "VALUES (3, %s, %s, 0)",
        ("003_m3.sql", sha256_file(path)),
    )
    conn.commit()
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(HistoryIntegrityError, match="does not start at 001"):
        runner.apply()


def test_unbaselined_legacy_nonpublic_objects_refuse(pg_conn, tmp_path: Path) -> None:
    conn, schema = pg_conn
    _write(tmp_path, 1, "a", "CREATE TABLE should_not_run (id int);")
    # View + sequence in non-public schema — no public base tables.
    conn.execute(f'CREATE SEQUENCE "{schema}".legacy_seq')
    conn.execute(f'CREATE VIEW "{schema}".legacy_view AS SELECT 1 AS x')
    conn.commit()
    runner = MigrationRunner(conn, tmp_path)
    assert runner.is_unbaselined_legacy()
    with pytest.raises(BaselineRequiredError):
        runner.apply()
    assert conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='should_not_run'"
    ).fetchone()[0] == 0


def test_baseline_stamps_without_sql_then_status_current(pg_conn, tmp_path: Path) -> None:
    conn, _ = pg_conn
    _write(tmp_path, 1, "a", "CREATE TABLE a (id int);")
    _write(tmp_path, 2, "b", "CREATE TABLE b (id int);")
    conn.execute("CREATE TABLE already_live (id int)")
    conn.commit()
    dbname = conn.execute("SELECT current_database()").fetchone()[0]
    runner = MigrationRunner(conn, tmp_path)
    with pytest.raises(BaselineRequiredError):
        runner.apply()
    stamped = runner.baseline(
        through=2,
        confirm_baseline=2,
        expect_database=dbname,
    )
    assert [m.version for m in stamped] == [1, 2]
    assert conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='a'"
    ).fetchone()[0] == 0
    assert runner.apply() == []
    rows = runner.status_rows()
    assert all(r.state.value == "applied" for r in rows)
