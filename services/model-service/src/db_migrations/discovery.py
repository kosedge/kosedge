"""Discover and validate numbered SQL migration files."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import MigrationSequenceError

_FILENAME_RE = re.compile(r"^(\d+)_(.+)\.sql$", re.IGNORECASE)


@dataclass(frozen=True)
class MigrationFile:
    version: int
    filename: str
    path: Path
    checksum: str

    @property
    def padded_version(self) -> str:
        return f"{self.version:03d}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_migrations(migrations_dir: Path) -> list[MigrationFile]:
    """Load ``*.sql`` migrations and return them in numeric version order."""
    if not migrations_dir.is_dir():
        raise MigrationSequenceError(f"migrations directory not found: {migrations_dir}")

    by_version: dict[int, MigrationFile] = {}
    unparsed: list[str] = []

    for path in sorted(migrations_dir.glob("*.sql")):
        match = _FILENAME_RE.match(path.name)
        if not match:
            unparsed.append(path.name)
            continue
        version = int(match.group(1))
        if version in by_version:
            raise MigrationSequenceError(
                f"duplicate migration version {version}: "
                f"{by_version[version].filename} and {path.name}"
            )
        by_version[version] = MigrationFile(
            version=version,
            filename=path.name,
            path=path,
            checksum=sha256_file(path),
        )

    if unparsed:
        raise MigrationSequenceError(
            "unparseable migration filename(s) (expected NNN_name.sql): "
            + ", ".join(sorted(unparsed))
        )

    migrations = [by_version[v] for v in sorted(by_version)]
    validate_sequence(migrations)
    return migrations


def validate_sequence(migrations: list[MigrationFile]) -> None:
    """Refuse duplicates (already filtered) and missing sequence numbers 1..N."""
    if not migrations:
        return

    versions = [m.version for m in migrations]
    if versions != sorted(versions):
        raise MigrationSequenceError("migrations are not sorted by numeric version")

    expected = list(range(1, versions[-1] + 1))
    missing = [v for v in expected if v not in versions]
    if missing:
        preview = ", ".join(f"{v:03d}" for v in missing[:12])
        more = "" if len(missing) <= 12 else f" (+{len(missing) - 12} more)"
        raise MigrationSequenceError(
            f"missing migration sequence number(s): {preview}{more}"
        )

    # Contiguous 1..N implies no duplicates; still assert uniqueness.
    if len(set(versions)) != len(versions):
        raise MigrationSequenceError("duplicate migration versions in sequence")
