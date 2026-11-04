"""Runtime forbidden-call guard for produce_chain / fixture-chain assembly.

Shared helper for Worker B (`scripts/nfl/t5194u-ab-chain.py` should assert
`last_guard_report()["guard_active"] is True` after a produce).

Routes attempts into assemble.note_forbidden_call:
- sys.meta_path finder for forbidden_import_names()
- socket.socket.connect + socket.getaddrinfo
- wrap forbidden_name_tokens() symbols already loaded
"""

from __future__ import annotations

import socket
import sys
from contextlib import contextmanager
from importlib.abc import MetaPathFinder
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

_GUARD_DEPTH = 0
_GUARD_ACTIVE = False
_LAST_RUN_HAD_GUARD = False
_FINDER: Optional["ForbiddenImportFinder"] = None
_ORIG_CONNECT: Any = None
_ORIG_GETADDRINFO: Any = None
_TOKEN_ORIG: List[Tuple[Any, str, Any]] = []


def _note(name: str) -> None:
    from src.services.nfl_fixture_assembly.assemble import note_forbidden_call

    note_forbidden_call(name)


def _forbidden_imports() -> frozenset[str]:
    from src.services.nfl_fixture_assembly.assemble import forbidden_import_names

    return forbidden_import_names()


def _forbidden_tokens() -> frozenset[str]:
    from src.services.nfl_fixture_assembly.assemble import forbidden_name_tokens

    return forbidden_name_tokens()


def _is_forbidden_module(fullname: str) -> bool:
    forbidden = _forbidden_imports()
    if fullname in forbidden:
        return True
    for name in forbidden:
        if fullname == name or fullname.startswith(name + "."):
            return True
        if name.startswith(fullname + ".") and fullname.split(".")[0] == name.split(".")[0]:
            # do not treat a short prefix like "src" as forbidden
            continue
    top = fullname.split(".", 1)[0]
    return top in forbidden


class ForbiddenImportFinder(MetaPathFinder):
    def find_spec(self, fullname: str, path: Any, target: Any = None):  # type: ignore[override]
        if _is_forbidden_module(fullname):
            _note(f"import:{fullname}")
        return None


def _guarded_connect(self: Any, *args: Any, **kwargs: Any) -> Any:
    _note("socket.connect")


def _guarded_getaddrinfo(*args: Any, **kwargs: Any) -> Any:
    _note("socket.getaddrinfo")


def _wrap_token(token: str, original: Any) -> Callable[..., Any]:
    def _blocked(*args: Any, **kwargs: Any) -> Any:
        _note(token)

    _blocked._fixture_guard_wrap = True  # type: ignore[attr-defined]
    _blocked._fixture_guard_orig = original  # type: ignore[attr-defined]
    return _blocked


def _install_socket_patches() -> None:
    global _ORIG_CONNECT, _ORIG_GETADDRINFO
    if _ORIG_CONNECT is None:
        _ORIG_CONNECT = socket.socket.connect
        _ORIG_GETADDRINFO = socket.getaddrinfo
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]


def _restore_socket_patches() -> None:
    global _ORIG_CONNECT, _ORIG_GETADDRINFO
    if _ORIG_CONNECT is not None:
        socket.socket.connect = _ORIG_CONNECT  # type: ignore[method-assign]
        _ORIG_CONNECT = None
    if _ORIG_GETADDRINFO is not None:
        socket.getaddrinfo = _ORIG_GETADDRINFO  # type: ignore[assignment]
        _ORIG_GETADDRINFO = None


def _install_token_wraps() -> None:
    tokens = _forbidden_tokens()
    for _mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        for token in tokens:
            try:
                obj = getattr(mod, token, None)
            except Exception:
                continue
            if not callable(obj) or getattr(obj, "_fixture_guard_wrap", False):
                continue
            _TOKEN_ORIG.append((mod, token, obj))
            try:
                setattr(mod, token, _wrap_token(token, obj))
            except Exception:
                _TOKEN_ORIG.pop()


def _restore_token_wraps() -> None:
    while _TOKEN_ORIG:
        mod, token, orig = _TOKEN_ORIG.pop()
        try:
            setattr(mod, token, orig)
        except Exception:
            continue


def _install_finder() -> None:
    global _FINDER
    if _FINDER is None:
        _FINDER = ForbiddenImportFinder()
    if _FINDER not in sys.meta_path:
        sys.meta_path.insert(0, _FINDER)


def _restore_finder() -> None:
    global _FINDER
    if _FINDER is not None and _FINDER in sys.meta_path:
        sys.meta_path.remove(_FINDER)
    _FINDER = None


def install_chain_guard() -> None:
    """Idempotent install. Nested installs increment depth."""
    global _GUARD_DEPTH, _GUARD_ACTIVE, _LAST_RUN_HAD_GUARD
    _GUARD_DEPTH += 1
    if _GUARD_DEPTH > 1:
        _GUARD_ACTIVE = True
        _LAST_RUN_HAD_GUARD = True
        return
    _install_finder()
    _install_socket_patches()
    _install_token_wraps()
    _GUARD_ACTIVE = True
    _LAST_RUN_HAD_GUARD = True


def uninstall_chain_guard() -> None:
    global _GUARD_DEPTH, _GUARD_ACTIVE
    if _GUARD_DEPTH <= 0:
        _GUARD_ACTIVE = False
        return
    _GUARD_DEPTH -= 1
    if _GUARD_DEPTH > 0:
        return
    _restore_finder()
    _restore_socket_patches()
    _restore_token_wraps()
    _GUARD_ACTIVE = False


def guard_active() -> bool:
    return _GUARD_ACTIVE and _GUARD_DEPTH > 0


def last_guard_report() -> Dict[str, Any]:
    """B helper: after produce_chain, assert report['guard_active'] is True."""
    from src.services.nfl_fixture_assembly.assemble import FORBIDDEN_CALL_ATTEMPTS

    return {
        "guard_active": bool(_LAST_RUN_HAD_GUARD),
        "guard_installed": guard_active(),
        "forbidden_call_attempts": len(FORBIDDEN_CALL_ATTEMPTS),
        "attempts": list(FORBIDDEN_CALL_ATTEMPTS),
    }


class _GuardState:
    __slots__ = ("active",)

    def __init__(self, active: bool) -> None:
        self.active = active


@contextmanager
def chain_guard() -> Iterator[_GuardState]:
    install_chain_guard()
    try:
        if not guard_active():
            _note("guard_inactive")
        yield _GuardState(active=True)
    finally:
        uninstall_chain_guard()


def run_under_chain_guard(fn: Callable[[], Any]) -> Any:
    with chain_guard():
        return fn()
