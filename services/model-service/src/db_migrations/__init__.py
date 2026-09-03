"""Tracked raw-SQL migration runner for infra/db/*.sql.

Bootstrap of ``schema_migrations`` is owned by this package (not a numbered
SQL file) so the runner can track history before any migration exists.
"""

from .discovery import MigrationFile, discover_migrations, validate_sequence
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
from .runner import MigrationRunner, MigrationStatusRow, SCHEMA_MIGRATIONS_DDL

__all__ = [
    "SCHEMA_MIGRATIONS_DDL",
    "BaselineConfirmationError",
    "BaselineRequiredError",
    "ChecksumDriftError",
    "HistoryIntegrityError",
    "MigrationApplyError",
    "MigrationError",
    "MigrationFile",
    "MigrationLockError",
    "MigrationRunner",
    "MigrationSequenceError",
    "MigrationStatusRow",
    "discover_migrations",
    "validate_sequence",
]
