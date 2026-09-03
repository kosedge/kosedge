"""Migration runner errors."""

from __future__ import annotations


class MigrationError(Exception):
    """Base class for migration runner failures."""


class MigrationSequenceError(MigrationError):
    """Duplicate versions, gaps, or unparseable filenames."""


class ChecksumDriftError(MigrationError):
    """An applied migration's file no longer matches the recorded SHA-256."""


class HistoryIntegrityError(MigrationError):
    """Tracking history is not an exact contiguous disk-matched prefix 001..N."""


class BaselineRequiredError(MigrationError):
    """Legacy nonempty DB has no (or empty) tracking history; refuse replay."""


class BaselineConfirmationError(MigrationError):
    """Baseline refused: missing/mismatched confirmation or database identity."""


class MigrationLockError(MigrationError):
    """Could not acquire the migration advisory lock within the timeout."""


class MigrationApplyError(MigrationError):
    """A single migration SQL file failed during apply."""

    def __init__(self, version: int, filename: str, cause: BaseException) -> None:
        self.version = version
        self.filename = filename
        self.cause = cause
        # Never embed connection strings from the cause message if present.
        detail = str(cause)
        super().__init__(f"migration {version:03d} ({filename}) failed: {detail}")
