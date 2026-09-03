"""Resolve the migrations directory and DATABASE_URL helpers."""

from __future__ import annotations

import os
from pathlib import Path


def migrations_dir_candidates(here: Path | None = None) -> list[Path]:
    """Build ordered candidate paths for ``infra/db`` without unsafe parent indexing.

    Railway images install the package at ``/app/src/db_migrations/...`` (only
    parents[0..3] exist). Indexing ``parents[4]`` must never raise while building
    this list — otherwise even the hard-coded ``/app/infra/db`` candidate is skipped.
    """
    base = (here or Path(__file__)).resolve()
    candidates: list[Path] = [
        Path("/app/infra/db"),  # Docker/Railway staged copy (prefer first)
    ]
    # parents[2] = service root (…/model-service or /app); parents[4] = monorepo root
    # when deep enough. Length-check so shallow installs cannot IndexError.
    for idx in (2, 4):
        if len(base.parents) > idx:
            candidates.append(base.parents[idx] / "infra" / "db")
    candidates.extend(
        [
            Path.cwd() / "infra" / "db",
            Path.cwd().parent / "infra" / "db",
            Path.cwd().parent.parent / "infra" / "db",
        ]
    )
    for parent in base.parents:
        candidates.append(parent / "infra" / "db")

    seen: set[Path] = set()
    uniq: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            uniq.append(path)
    return uniq


def resolve_migrations_dir(
    explicit: str | Path | None = None,
    *,
    here: Path | None = None,
) -> Path:
    """Locate ``infra/db`` SQL migrations.

    Search order:
    1. Explicit CLI / API path
    2. ``KOSEDGE_MIGRATIONS_DIR``
    3. Staged copy beside the package (Railway image: ``/app/infra/db``)
    4. Walk parents for repo-root ``infra/db``
    """
    if explicit is not None:
        path = Path(explicit).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"migrations directory not found: {path}")
        return path

    env = os.environ.get("KOSEDGE_MIGRATIONS_DIR", "").strip()
    if env:
        path = Path(env).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(
                f"KOSEDGE_MIGRATIONS_DIR is set but not a directory: {path}"
            )
        return path

    for candidate in migrations_dir_candidates(here):
        if candidate.is_dir():
            return candidate.resolve()

    raise FileNotFoundError(
        "could not locate infra/db migrations; pass --migrations-dir or set "
        "KOSEDGE_MIGRATIONS_DIR (stage via scripts/db/stage_migrations_into_model_service.sh "
        "for Railway images)"
    )


def normalize_database_url(url: str) -> str:
    """Accept postgres:// / postgresql:// URLs for psycopg.connect."""
    raw = url.strip()
    if raw.startswith("postgresql+psycopg://"):
        return "postgresql://" + raw[len("postgresql+psycopg://") :]
    if raw.startswith("postgresql+psycopg2://"):
        return "postgresql://" + raw[len("postgresql+psycopg2://") :]
    if raw.startswith("postgres://"):
        return "postgresql://" + raw[len("postgres://") :]
    return raw


def require_database_url() -> str:
    """Read DATABASE_URL from the environment only. Never accept CLI secrets."""
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required. "
            "Pass credentials via the environment only — there is no --database-url flag. "
            "Do not embed credentials in code, docs, or logs."
        )
    return normalize_database_url(url)
