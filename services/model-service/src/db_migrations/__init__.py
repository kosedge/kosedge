"""Tracked raw-SQL migration runner for infra/db/*.sql.

Bootstrap of ``schema_migrations`` is owned by this package (not a numbered
SQL file) so the runner can track history before any migration exists.
"""

from .discovery import MigrationFile, discover_migrations, validate_sequence
from .errors import (
    BaselineRequiredError,
    ChecksumDriftError,
    MigrationApplyError,
    MigrationError,
    MigrationSequenceError,
)
from .runner import MigrationRunner, MigrationStatusRow

__all__ = [
    "BaselineRequiredError",
    "ChecksumDriftError",
    "MigrationApplyError",
    "MigrationError",
    "MigrationFile",
    "MigrationRunner",
    "MigrationSequenceError",
    "MigrationStatusRow",
    "discover_migrations",
    "validate_sequence",
]
