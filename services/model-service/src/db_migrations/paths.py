"""Resolve the migrations directory and DATABASE_URL helpers."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_migrations_dir(explicit: str | Path | None = None) -> Path:
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

    here = Path(__file__).resolve()
    candidates = [
        Path("/app/infra/db"),
        here.parents[2] / "infra" / "db",  # services/model-service/infra/db (staged)
        here.parents[4] / "infra" / "db",  # repo-root/infra/db from src/db_migrations
        Path.cwd() / "infra" / "db",
        Path.cwd().parent / "infra" / "db",
        Path.cwd().parent.parent / "infra" / "db",
    ]
    # Also walk parents for infra/db (robust to package moves).
    for parent in here.parents:
        candidates.append(parent / "infra" / "db")
    for candidate in candidates:
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


def require_database_url(explicit: str | None = None) -> str:
    url = (explicit or os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required (or pass --database-url). "
            "Do not embed credentials in code or docs."
        )
    return normalize_database_url(url)
