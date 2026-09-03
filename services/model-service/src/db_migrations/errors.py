"""Migration runner errors."""

from __future__ import annotations


class MigrationError(Exception):
    """Base class for migration runner failures."""


class MigrationSequenceError(MigrationError):
    """Duplicate versions, gaps, or unparseable filenames."""


class ChecksumDriftError(MigrationError):
    """An applied migration's file no longer matches the recorded SHA-256."""


class BaselineRequiredError(MigrationError):
    """Legacy nonempty DB has no tracking rows; refuse to replay history."""


class MigrationApplyError(MigrationError):
    """A single migration SQL file failed during apply."""

    def __init__(self, version: int, filename: str, cause: BaseException) -> None:
        self.version = version
        self.filename = filename
        self.cause = cause
        super().__init__(f"migration {version:03d} ({filename}) failed: {cause}")
