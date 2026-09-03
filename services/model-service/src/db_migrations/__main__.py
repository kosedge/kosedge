"""CLI: python -m src.db_migrations {status|apply|up|baseline|stamp|check-integrity}"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .discovery import discover_migrations
from .errors import (
    BaselineConfirmationError,
    BaselineRequiredError,
    ChecksumDriftError,
    HistoryIntegrityError,
    MigrationApplyError,
    MigrationError,
    MigrationLockError,
    MigrationSequenceError,
)
from .paths import require_database_url, resolve_migrations_dir
from .runner import MigrationRunner, MigrationState, format_status


def _connect(database_url: str):
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "psycopg is required (model-service dependency). "
            "pip install -r services/model-service/requirements.txt"
        ) from exc
    # autocommit=False so DDL + tracking row share a transaction per migration.
    return psycopg.connect(database_url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.db_migrations",
        description=(
            "Tracked raw-SQL migrations for infra/db. "
            "schema_migrations is bootstrapped by this runner (not a numbered file). "
            "DATABASE_URL must come from the environment (no --database-url)."
        ),
    )
    parser.add_argument(
        "--migrations-dir",
        default=None,
        help="Path to infra/db (default: auto-detect / KOSEDGE_MIGRATIONS_DIR)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Show applied / pending / drifted")
    status.add_argument(
        "--require-current",
        action="store_true",
        help=(
            "Exit 1 if any migration is pending or drifted, history is invalid, "
            "or the DB is an unbaselined legacy warehouse. Read-only regarding "
            "numbered SQL; never stamps or applies migrations."
        ),
    )
    status.add_argument(
        "--bootstrap-tracking",
        action="store_true",
        help=(
            "Create schema_migrations if missing before reading status "
            "(still does not stamp or apply numbered SQL)."
        ),
    )

    apply = sub.add_parser("apply", aliases=["up"], help="Apply pending migrations")
    apply.add_argument(
        "--dry-run",
        action="store_true",
        help="Print pending migrations without executing SQL",
    )
    apply.add_argument(
        "--lock-timeout-seconds",
        type=int,
        default=30,
        help="Advisory lock wait bound before failing loudly (default 30)",
    )

    baseline = sub.add_parser(
        "baseline",
        aliases=["stamp"],
        help=(
            "Stamp migrations 1..THROUGH without executing SQL. "
            "Initial baseline only (empty tracker). Requires confirmation tokens."
        ),
    )
    baseline.add_argument(
        "--through",
        type=int,
        required=True,
        help="Highest version to stamp (e.g. 054 for current KosEdge warehouse cutover)",
    )
    baseline.add_argument(
        "--confirm-baseline",
        type=int,
        required=True,
        help="Must exactly equal --through (deliberate confirmation token)",
    )
    baseline.add_argument(
        "--expect-database",
        type=str,
        required=True,
        help=(
            "Must exactly equal current_database() on the server "
            "(DB identity check; never pass a URL here)"
        ),
    )
    baseline.add_argument(
        "--lock-timeout-seconds",
        type=int,
        default=30,
        help="Advisory lock wait bound before failing loudly (default 30)",
    )

    sub.add_parser(
        "check-integrity",
        help="Repo-only sequence validation (no database). Safe for CI.",
    )
    return parser


def cmd_check_integrity(migrations_dir: Path) -> int:
    migrations = discover_migrations(migrations_dir)
    print(f"ok: {len(migrations)} migrations in {migrations_dir}")
    for mig in migrations:
        print(f"  {mig.version:03d}  {mig.checksum}  {mig.filename}")
    return 0


def cmd_status(
    runner: MigrationRunner,
    *,
    require_current: bool,
    bootstrap_tracking: bool,
) -> int:
    unbaselined = False
    try:
        if runner.tracking_table_exists():
            unbaselined = runner.is_unbaselined_legacy()
            rows = runner.status_rows()  # validates history when nonempty
        elif bootstrap_tracking:
            runner.ensure_tracking_table()
            unbaselined = runner.is_unbaselined_legacy()
            rows = runner.status_rows()
        else:
            unbaselined = runner.non_system_user_object_count(exclude_tracking=False) > 0
            rows = runner.status_rows()
    except (HistoryIntegrityError, ChecksumDriftError) as exc:
        print(f"history FAILED: {exc}", file=sys.stderr)
        return 1 if require_current else 1  # always fail closed on bad history

    print(format_status(rows, unbaselined_legacy=unbaselined))

    if not require_current:
        return 0

    if unbaselined:
        print(
            "require-current FAILED: unbaselined legacy database "
            "(explicit baseline required before apply).",
            file=sys.stderr,
        )
        return 1

    bad = [r for r in rows if r.state is not MigrationState.APPLIED]
    if bad:
        print(
            f"require-current FAILED: {len(bad)} migration(s) not cleanly applied.",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_apply(runner: MigrationRunner, *, dry_run: bool) -> int:
    if dry_run:
        if runner.is_unbaselined_legacy():
            raise BaselineRequiredError(
                "dry-run: apply would refuse (unbaselined legacy database)"
            )
        if runner.tracking_table_exists():
            runner.validate_applied_history()
        pending = [
            r for r in runner.status_rows() if r.state is MigrationState.PENDING
        ]
        if not pending:
            print("dry-run: already current (no pending migrations)")
            return 0
        print("dry-run: would apply:")
        for row in pending:
            print(f"  {row.version:03d}  {row.filename}")
        return 0

    applied = runner.apply()
    if not applied:
        print("ok: already current (no pending migrations)")
        return 0
    for mig in applied:
        print(f"applied: {mig.version:03d}  {mig.filename}  checksum={mig.checksum}")
    print(f"ok: applied {len(applied)} migration(s)")
    return 0


def cmd_baseline(
    runner: MigrationRunner,
    *,
    through: int,
    confirm_baseline: int,
    expect_database: str,
) -> int:
    stamped = runner.baseline(
        through=through,
        confirm_baseline=confirm_baseline,
        expect_database=expect_database,
    )
    if not stamped:
        print(f"ok: baseline already covered through {through:03d}")
        return 0
    for mig in stamped:
        print(f"stamped: {mig.version:03d}  {mig.filename}  checksum={mig.checksum}")
    print(f"ok: baselined {len(stamped)} migration(s) through {through:03d}")
    print(
        "note: baseline is operator attestation of applied history; "
        "it does not inspect whether each historical DDL effect exists."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        migrations_dir = resolve_migrations_dir(args.migrations_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "check-integrity":
        try:
            return cmd_check_integrity(migrations_dir)
        except MigrationSequenceError as exc:
            print(f"integrity FAILED: {exc}", file=sys.stderr)
            return 1

    try:
        database_url = require_database_url()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        with _connect(database_url) as conn:
            lock_timeout = getattr(args, "lock_timeout_seconds", 30)
            runner = MigrationRunner(
                conn,
                migrations_dir,
                lock_timeout_seconds=lock_timeout,
            )
            if args.command == "status":
                return cmd_status(
                    runner,
                    require_current=args.require_current,
                    bootstrap_tracking=args.bootstrap_tracking,
                )
            if args.command in ("apply", "up"):
                return cmd_apply(runner, dry_run=args.dry_run)
            if args.command in ("baseline", "stamp"):
                return cmd_baseline(
                    runner,
                    through=args.through,
                    confirm_baseline=args.confirm_baseline,
                    expect_database=args.expect_database,
                )
            parser.error(f"unknown command: {args.command}")
            return 2
    except BaselineRequiredError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except BaselineConfirmationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except ChecksumDriftError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except HistoryIntegrityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except MigrationLockError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6
    except MigrationApplyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    except MigrationSequenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except MigrationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
