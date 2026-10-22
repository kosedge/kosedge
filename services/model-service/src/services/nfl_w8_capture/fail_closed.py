"""RA-1 / RA-6 fail-closed guards for the frozen W8 builder (F-0..F-6)."""

from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

W8_CAPTURE_BUILD_ENV = "W8_CAPTURE_BUILD"

_DB_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+\S*("
    r"sqlalchemy|fetch_prior_primary_qbs|fetch_current_qb1|"
    r"fetch_roster_sets|fetch_skill_yards|fetch_team_proe_map"
    r")",
    re.MULTILINE,
)


class FailClosedError(RuntimeError):
    """W8 builder STOP. Invalid or missing evidence stays in n as FAIL."""


def collect_nfl_env_overrides() -> list[str]:
    """F-4: record every NFL_* name set on this build."""
    return sorted(key for key in os.environ if key.startswith("NFL_"))


def record_nfl_env_overrides() -> list[str]:
    """F-4: record every NFL_* name. Any override is a STOP."""
    names = collect_nfl_env_overrides()
    if names:
        raise FailClosedError(
            f"F-4 STOP: NFL_* environment overrides set: {names}"
        )
    return names


def assert_src_not_shadowed() -> Path:
    """F-5: refuse a regular ``src`` earlier on sys.path that would shadow us."""
    expected_src = Path(__file__).resolve().parents[2]  # .../model-service/src
    for entry in sys.path:
        if entry is None or entry == "":
            candidate = Path.cwd() / "src"
        else:
            candidate = Path(entry) / "src"
        if not candidate.exists():
            continue
        is_regular = (candidate / "__init__.py").is_file()
        has_services = (candidate / "services").exists()
        if not is_regular and not has_services:
            continue
        resolved = candidate.resolve()
        if resolved != expected_src:
            raise FailClosedError(
                f"F-5 STOP: src on sys.path is shadowed by {resolved} "
                f"(expected {expected_src})"
            )
        break
    return expected_src


def refuse_db_loaders(session: Any = None) -> None:
    """F-6: builder must never reach DB loaders."""
    if os.environ.get("DATABASE_URL"):
        raise FailClosedError(
            "F-6 STOP: builder reached DB loaders (DATABASE_URL is set)"
        )
    if session is not None:
        raise FailClosedError("F-6 STOP: builder received a DB session")


def refuse_if_w8_reached_db_loader(name: str) -> None:
    """F-6: production fetchers STOP if invoked during a W8 build."""
    if os.environ.get(W8_CAPTURE_BUILD_ENV):
        raise FailClosedError(f"F-6 STOP: builder reached DB loader {name}")


@contextmanager
def w8_build_context() -> Iterator[None]:
    """Mark the process as inside a W8 build so DB loaders fail closed."""
    prev = os.environ.get(W8_CAPTURE_BUILD_ENV)
    os.environ[W8_CAPTURE_BUILD_ENV] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(W8_CAPTURE_BUILD_ENV, None)
        else:
            os.environ[W8_CAPTURE_BUILD_ENV] = prev


def db_loader_import_hits(root: Path | None = None) -> list[str]:
    """F-6: W8 capture source must not import DB loaders or SQLAlchemy."""
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    hits: list[str] = []
    for path in base.glob("*.py"):
        if path.name == "fail_closed.py":
            continue
        text = path.read_text(encoding="utf-8")
        if _DB_IMPORT_RE.search(text):
            hits.append(path.name)
    return hits


def run_builder_guards(*, session: Any = None) -> dict[str, Any]:
    """Run F-4 / F-5 / F-6 before any W8 seal work."""
    refuse_db_loaders(session)
    src_root = assert_src_not_shadowed()
    nfl_env = record_nfl_env_overrides()
    return {
        "nfl_env_overrides": nfl_env,
        "src_root": str(src_root),
        "db_session": None,
    }
