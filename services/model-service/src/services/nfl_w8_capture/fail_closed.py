"""RA-1 / RA-6 fail-closed guards for the frozen W8 builder (F-0..F-6)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional


class FailClosedError(RuntimeError):
    """W8 builder STOP. Invalid or missing evidence stays in n as FAIL."""


def record_nfl_env_overrides() -> list[str]:
    """F-4: record every NFL_* name. Any override is a STOP."""
    names = sorted(key for key in os.environ if key.startswith("NFL_"))
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
        services = candidate / "services"
        if not services.exists():
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
