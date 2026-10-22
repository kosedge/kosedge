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
        "redis",
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

_IMPORT_LINE_RE = re.compile(r"^\s*(?:from|import)\s+(.+)$", re.DOTALL)
_DYNAMIC_IMPORT_RE = re.compile(
    r"""(?:importlib\s*\.\s*import_module|__import__)\s*\(\s*(['"])([^'"]+)\1"""
)


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


def _require_explicit_stop_path(path: Path | str | None) -> Path:
    """K-3: STOP.json is written only to an explicit absolute path, never cwd."""
    if path is None or str(path).strip() == "":
        raise FailClosedError(
            "K-3 STOP: STOP.json requires an explicit absolute path (never cwd)"
        )
    out = Path(path)
    if not out.is_absolute():
        raise FailClosedError(
            "K-3 STOP: STOP.json requires an explicit absolute path (never cwd)"
        )
    return out


def unique_stop_record_path(path: Path) -> Path:
    """Noclobber: if path exists, pick STOP.N.json beside it."""
    if not path.exists():
        return path
    n = 1
    while True:
        candidate = path.with_name(f"{path.stem}.{n}{path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def write_stop_record(
    path: Path | str | None,
    names: list[str],
    *,
    reason: str,
) -> Path:
    """K-3: persist STOP names (never values) before the exception exits."""
    requested = _require_explicit_stop_path(path)
    requested.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "STOP",
        "reason": reason,
        "env_names": list(names),
        "values_recorded": False,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    n = 0
    target = requested
    while True:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(target, flags, 0o644)
        except FileExistsError:
            n += 1
            target = requested.with_name(f"{requested.stem}.{n}{requested.suffix}")
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        return target


def persist_stop_and_raise(
    names: list[str],
    *,
    reason: str,
    stop_record_path: Path | str | None,
) -> None:
    try:
        write_stop_record(stop_record_path, names, reason=reason)
    except FailClosedError as exc:
        if "explicit absolute path" in str(exc):
            raise FailClosedError(
                f"{reason}: {names} (K-3: STOP.json path required; never cwd)"
            ) from exc
        raise
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
    """F-6: STOP only inside a W8 build. Session-less callers outside W8 stay open."""
    _ = session
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


def _tokens_are_banned(blob: str) -> bool:
    return any(token in BANNED_IMPORT_NAMES for token in re.split(r"[^\w]+", blob) if token)


def logical_import_units(text: str) -> list[str]:
    """Join parenthesized / backslash-continued import statements into units."""
    units: list[str] = []
    pending: list[str] | None = None
    depth = 0
    for raw in text.splitlines():
        line = raw.split("#", 1)[0]
        if pending is not None:
            pending.append(line)
            depth += line.count("(") - line.count(")")
            continued = line.rstrip().endswith("\\")
            if depth <= 0 and not continued:
                units.append("\n".join(pending))
                pending = None
            continue
        if not _IMPORT_LINE_RE.match(line):
            continue
        depth = line.count("(") - line.count(")")
        if depth > 0 or line.rstrip().endswith("\\"):
            pending = [line]
        else:
            units.append(line)
    if pending:
        units.append("\n".join(pending))
    return units


def import_line_is_banned(line: str) -> bool:
    """True if an import line or dynamic import names a banned module (K-2)."""
    flat = " ".join(part.rstrip("\\") for part in line.splitlines())
    match = _IMPORT_LINE_RE.match(flat)
    if match and _tokens_are_banned(match.group(1)):
        return True
    for hit in _DYNAMIC_IMPORT_RE.finditer(flat):
        if _tokens_are_banned(hit.group(2)):
            return True
    return False


def source_has_banned_import(text: str) -> bool:
    """K-2: scan joined parenthesized imports plus importlib / __import__."""
    for unit in logical_import_units(text):
        if import_line_is_banned(unit):
            return True
    for hit in _DYNAMIC_IMPORT_RE.finditer(text):
        if _tokens_are_banned(hit.group(2)):
            return True
    return False


def db_loader_import_hits(root: Path | None = None) -> list[str]:
    """F-6 / K-2: W8 capture source must not import DB loaders or brokers."""
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    hits: list[str] = []
    for path in sorted(base.rglob("*.py")):
        if path.name == "fail_closed.py" and root is None:
            continue
        text = path.read_text(encoding="utf-8")
        if source_has_banned_import(text):
            hits.append(path.name)
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
