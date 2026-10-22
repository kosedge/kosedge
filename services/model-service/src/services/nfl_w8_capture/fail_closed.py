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
_FROM_IMPORT_RE = re.compile(
    r"^\s*from\s+(\S+)\s+import\s+(.+)$", re.DOTALL
)
_IMPORT_AS_RE = re.compile(
    r"^\s*import\s+(\S+)(?:\s+as\s+(\w+))?\s*$"
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
    import_names: list[str] | None = None,
) -> Path:
    """K-3: persist STOP names (never values) before the exception exits."""
    requested = _require_explicit_stop_path(path)
    requested.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "STOP",
        "reason": reason,
        "env_names": list(names),
        "import_names": list(import_names or []),
        "values_recorded": False,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    target = unique_stop_record_path(requested)
    while True:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(target, flags, 0o644)
        except FileExistsError:
            target = unique_stop_record_path(requested)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        return target


def persist_stop_and_raise(
    names: list[str],
    *,
    reason: str,
    stop_record_path: Path | str | None,
    import_names: list[str] | None = None,
) -> None:
    recorded = list(import_names or names)
    try:
        write_stop_record(
            stop_record_path,
            names,
            reason=reason,
            import_names=import_names,
        )
    except FailClosedError as exc:
        if "explicit absolute path" in str(exc):
            raise FailClosedError(
                f"{reason}: {recorded} (K-3: STOP.json path required; never cwd)"
            ) from exc
        raise
    raise FailClosedError(f"{reason}: {recorded}")


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


def _flatten_import_unit(unit: str) -> str:
    return " ".join(part.rstrip("\\") for part in unit.splitlines())


def _tokens_from(blob: str) -> list[str]:
    return [token for token in re.split(r"[^\w]+", blob) if token]


def _banned_tokens_in(blob: str) -> list[str]:
    return [token for token in _tokens_from(blob) if token in BANNED_IMPORT_NAMES]


def _parse_import_items(rest: str) -> list[tuple[str, str]]:
    body = rest.strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    items: list[tuple[str, str]] = []
    for raw in body.split(","):
        part = raw.strip()
        if not part:
            continue
        if " as " in part:
            orig, alias = part.split(" as ", 1)
            items.append((orig.strip(), alias.strip()))
        else:
            items.append((part, part))
    return items


def dynamic_import_callables(text: str) -> set[str]:
    """Call names that load a module by string, including aliases (K-2 (d))."""
    names = {
        "__import__",
        "importlib.import_module",
        "importlib.util.find_spec",
        "import_module",
        "find_spec",
    }
    for unit in logical_import_units(text):
        flat = _flatten_import_unit(unit)
        from_match = _FROM_IMPORT_RE.match(flat)
        if from_match:
            module = from_match.group(1)
            for orig, alias in _parse_import_items(from_match.group(2)):
                if module == "importlib" and orig == "import_module":
                    names.add(alias)
                if module == "importlib" and orig == "util":
                    names.add(f"{alias}.find_spec")
                if module == "importlib.util" and orig == "find_spec":
                    names.add(alias)
            continue
        as_match = _IMPORT_AS_RE.match(flat)
        if not as_match:
            continue
        module = as_match.group(1)
        bound = as_match.group(2) or module
        if module == "importlib":
            names.add(f"{bound}.import_module")
            names.add(f"{bound}.util.find_spec")
        elif module == "importlib.util":
            names.add(f"{bound}.find_spec")
    return names


def dynamic_import_targets(text: str) -> list[str]:
    """Module strings passed to importlib / __import__ / find_spec / aliases."""
    callables = sorted(dynamic_import_callables(text), key=len, reverse=True)
    if not callables:
        return []
    pattern = re.compile(
        r"(?<![\w])(?:"
        + "|".join(re.escape(name) for name in callables)
        + r")\s*\(\s*(['\"])([^'\"]+)\1"
    )
    return [hit.group(2) for hit in pattern.finditer(text)]


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


def banned_names_in_source(text: str) -> list[str]:
    """K-2: banned names from joined imports and dynamic loaders."""
    found: set[str] = set()
    for unit in logical_import_units(text):
        flat = _flatten_import_unit(unit)
        match = _IMPORT_LINE_RE.match(flat)
        if match:
            found.update(_banned_tokens_in(match.group(1)))
        found.update(_banned_tokens_in(" ".join(dynamic_import_targets(flat))))
    for target in dynamic_import_targets(text):
        found.update(_banned_tokens_in(target))
    return sorted(found)


def import_line_is_banned(line: str) -> bool:
    """True if an import line or dynamic import names a banned module (K-2)."""
    return bool(banned_names_in_source(line))


def source_has_banned_import(text: str) -> bool:
    """K-2: scan joined parenthesized imports plus importlib / __import__."""
    return bool(banned_names_in_source(text))


def db_loader_import_hits(root: Path | None = None) -> list[str]:
    """F-6 / K-2: W8 capture source must not import DB loaders or brokers."""
    return [name for name, _names in db_loader_import_findings(root)]


def db_loader_import_findings(
    root: Path | None = None,
) -> list[tuple[str, list[str]]]:
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    findings: list[tuple[str, list[str]]] = []
    for path in sorted(base.rglob("*.py")):
        if path.name == "fail_closed.py" and root is None:
            continue
        names = banned_names_in_source(path.read_text(encoding="utf-8"))
        if names:
            findings.append((path.name, names))
    return findings


def db_loader_banned_names(root: Path | None = None) -> list[str]:
    found: set[str] = set()
    for _filename, names in db_loader_import_findings(root):
        found.update(names)
    return sorted(found)


def refuse_banned_imports(
    *,
    root: Path | None = None,
    stop_record_path: Path | str | None = None,
) -> list[str]:
    """K-2: builder gate. A hit writes names to STOP.json and raises."""
    names = db_loader_banned_names(root)
    if names:
        persist_stop_and_raise(
            [],
            reason="K-2 STOP: banned import in W8 capture source",
            stop_record_path=stop_record_path,
            import_names=names,
        )
    return names


def run_builder_guards(
    *,
    session: Any = None,
    stop_record_path: Path | str | None = None,
    import_scan_root: Path | str | None = None,
) -> dict[str, Any]:
    """Run K-1 / K-2 / F-4 / F-5 / F-6 before any W8 seal or predict work."""
    env_names = record_nfl_env_overrides(stop_record_path=stop_record_path)
    refuse_db_loaders(session)
    src_root = assert_src_not_shadowed()
    scan_root = Path(import_scan_root) if import_scan_root is not None else None
    banned = refuse_banned_imports(
        root=scan_root,
        stop_record_path=stop_record_path,
    )
    return {
        "nfl_env_overrides": [n for n in env_names if n.startswith("NFL_")],
        "stop_env_names": env_names,
        "src_root": str(src_root),
        "db_session": None,
        "banned_import_names": banned,
    }
