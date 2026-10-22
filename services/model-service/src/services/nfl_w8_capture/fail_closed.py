"""RA-1 / RA-6 fail-closed guards for the frozen W8 builder (F-0..F-6)."""

from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

W8_CAPTURE_BUILD_ENV = "W8_CAPTURE_BUILD"
DEFAULT_STOP_RECORD_NAME = "STOP.json"

STOP_ENV_EXACT = frozenset({"DATABASE_URL", "REDIS_URL"})
STOP_ENV_PREFIXES = ("NFL_", "CELERY_")

# Imported names and modules that must not appear on a W8 capture import line.
BANNED_IMPORT_NAMES = frozenset(
    {
        "sqlalchemy",
        "celery",
        "kombu",
        "psycopg",
        "psycopg2",
        "db",
        "continuity_score",
        "nfl_tendency_pricing",
        "fetch_prior_primary_qbs",
        "fetch_current_qb1",
        "fetch_roster_sets",
        "fetch_skill_yards_by_player",
        "fetch_team_proe_map",
        "fetch_team_direction_rates",
    }
)

_IMPORT_LINE_RE = re.compile(r"^\s*(?:from|import)\s+(.+)$")


class FailClosedError(RuntimeError):
    """W8 builder STOP. Invalid or missing evidence stays in n as FAIL."""


def collect_stop_env_names() -> list[str]:
    """K-1: names only. DATABASE_URL, REDIS_URL, every NFL_* and CELERY_*."""
    names: list[str] = []
    for key in os.environ:
        if key in STOP_ENV_EXACT or any(key.startswith(p) for p in STOP_ENV_PREFIXES):
            names.append(key)
    return sorted(names)


def collect_nfl_env_overrides() -> list[str]:
    """F-4: NFL_* names only."""
    return [name for name in collect_stop_env_names() if name.startswith("NFL_")]


def write_stop_record(
    path: Path | str,
    names: list[str],
    *,
    reason: str,
) -> Path:
    """K-3: persist STOP names (never values) before the exception exits."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "STOP",
        "reason": reason,
        "env_names": list(names),
        "values_recorded": False,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def persist_stop_and_raise(
    names: list[str],
    *,
    reason: str,
    stop_record_path: Path | str | None,
) -> None:
    target = Path(stop_record_path) if stop_record_path else Path.cwd() / DEFAULT_STOP_RECORD_NAME
    write_stop_record(target, names, reason=reason)
    raise FailClosedError(f"{reason}: {names}")


def record_nfl_env_overrides(
    *,
    stop_record_path: Path | str | None = None,
) -> list[str]:
    """F-4 / K-1: record every STOP env name. Any override is a STOP."""
    names = collect_stop_env_names()
    if names:
        persist_stop_and_raise(
            names,
            reason="K-1/F-4 STOP: builder environment overrides set",
            stop_record_path=stop_record_path,
        )
    return names


def assert_src_not_shadowed() -> Path:
    """F-5: refuse a regular ``src`` earlier on sys.path that would shadow us."""
    expected_src = Path(__file__).resolve().parents[2]  # .../model-service/src
    for entry in sys.path:
        if entry is None or entry == "":
            base = Path.cwd()
        else:
            base = Path(entry)
        src_py = base / "src.py"
        if src_py.is_file():
            raise FailClosedError(
                f"F-5 STOP: src.py on sys.path would shadow the namespace ({src_py})"
            )
        candidate = base / "src"
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
    imported = sys.modules.get("src")
    if imported is not None:
        imported_file = getattr(imported, "__file__", None)
        if imported_file:
            resolved = Path(imported_file).resolve().parent
            if resolved != expected_src:
                raise FailClosedError(
                    f"F-5 STOP: already-imported src is {resolved} "
                    f"(expected {expected_src})"
                )
        for raw in list(getattr(imported, "__path__", []) or []):
            resolved = Path(raw).resolve()
            if resolved != expected_src and (resolved / "__init__.py").is_file():
                raise FailClosedError(
                    f"F-5 STOP: already-imported src.__path__ includes {resolved} "
                    f"(expected {expected_src})"
                )
    return expected_src


def refuse_db_loaders(session: Any = None) -> None:
    """F-6: builder must never reach DB loaders."""
    if os.environ.get("DATABASE_URL"):
        raise FailClosedError(
            "F-6 STOP: builder reached DB loaders (DATABASE_URL is set)"
        )
    if session is not None:
        raise FailClosedError("F-6 STOP: builder received a DB session")


def refuse_if_w8_reached_db_loader(name: str, session: Any = None) -> None:
    """F-6 / K-2: STOP if invoked during a W8 build or without a session."""
    if os.environ.get(W8_CAPTURE_BUILD_ENV) or session is None:
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


def import_line_is_banned(line: str) -> bool:
    """True if an import line names a banned module or symbol (K-2)."""
    match = _IMPORT_LINE_RE.match(line)
    if not match:
        return False
    tokens = re.split(r"[^\w]+", match.group(1))
    return any(token in BANNED_IMPORT_NAMES for token in tokens if token)


def db_loader_import_hits(root: Path | None = None) -> list[str]:
    """F-6 / K-2: W8 capture source must not import DB loaders or brokers."""
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    hits: list[str] = []
    for path in sorted(base.rglob("*.py")):
        if path.name == "fail_closed.py" and root is None:
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if import_line_is_banned(line):
                hits.append(path.name)
                break
    return hits


def run_builder_guards(
    *,
    session: Any = None,
    stop_record_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run K-1 / F-4 / F-5 / F-6 before any W8 seal or predict work."""
    env_names = record_nfl_env_overrides(stop_record_path=stop_record_path)
    refuse_db_loaders(session)
    src_root = assert_src_not_shadowed()
    return {
        "nfl_env_overrides": [n for n in env_names if n.startswith("NFL_")],
        "stop_env_names": env_names,
        "src_root": str(src_root),
        "db_session": None,
    }
