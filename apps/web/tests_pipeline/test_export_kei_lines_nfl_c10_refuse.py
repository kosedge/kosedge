"""Export KEI C10 refuse — EXISTING BUT UNVERIFIED → process evidence.

Lineage: eight-target #6 (fail closed on missing/invalid data) ·
#695 inventory preference (2) · `export_kei_lines_nfl.py` @ f5e3bb58.

Contract under test (source, not invented):
  except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
      return 1
  …then write OUT.

Synthetic fixtures + mocked urllib only. OUT redirected to tmp.
No model/Odds HTTP. No DB. No credential env reads. No new thresholds.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
REPO = WEB_ROOT.parent.parent
SCRIPT = WEB_ROOT / "scripts" / "export_kei_lines_nfl.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "export_kei_c10"
SUCCESS_FIXTURE = FIXTURE_DIR / "fair_lines_success.json"
MALFORMED_FIXTURE = FIXTURE_DIR / "malformed.json"
REAL_OUT = WEB_ROOT / "data" / "processed" / "kei_lines_nfl.json"

C10_BASE = "http://c10.test.invalid"
SENTINEL_BYTES = b"PREEXISTING-KEI-C10-SENTINEL\n"

# Script only reads these four env keys. Tests set them; secrets stay absent.
EXPORT_ENV = {
    "MODEL_SERVICE_URL": C10_BASE,
    "NFL_KEI_SEASON": "2026",
    "NFL_KEI_DAYS_AHEAD": "7",
    "NFL_KEI_INCLUDE_PAST_DAYS": "0",
}

CREDENTIAL_ENV_KEYS = (
    "ODDS_API_KEY",
    "THE_ODDS_API_KEY",
    "ODDS_API_KEY_NFL",
    "DATABASE_URL",
    "INTERNAL_API_SECRET",
    "RAILWAY_TOKEN",
    "MODEL_SERVICE_TOKEN",
    "AWS_SECRET_ACCESS_KEY",
    "STRIPE_SECRET_KEY",
)


def _load_export_mod():
    spec = importlib.util.spec_from_file_location(
        "export_kei_lines_nfl_c10_refuse", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bind_out(mod: Any, tmp_path: Path) -> Path:
    out = tmp_path / "processed" / "kei_lines_nfl.json"
    assert out.resolve() != REAL_OUT.resolve()
    mod.OUT = out
    return out


def _strip_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in EXPORT_ENV.items():
        monkeypatch.setenv(key, value)
    for key in CREDENTIAL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _ok_urlopen(body: bytes) -> Callable[..., Any]:
    def _urlopen(url: str, timeout: float | None = None):
        assert str(url).startswith(C10_BASE), url
        assert timeout == 30

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *exc: object) -> bool:
                return False

            def read(self) -> bytes:
                return body

        return _Resp()

    return _urlopen


def _raise_urlopen(exc: BaseException) -> Callable[..., Any]:
    def _urlopen(url: str, timeout: float | None = None):
        assert str(url).startswith(C10_BASE), url
        assert timeout == 30
        raise exc

    return _urlopen


def _http_error(code: int, msg: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url=f"{C10_BASE}/nfl/fair-lines",
        code=code,
        msg=msg,
        hdrs=None,
        fp=None,
    )


def _refuse_urlopen(mode: str) -> Callable[..., Any]:
    if mode == "http_503":
        return _raise_urlopen(_http_error(503, "Service Unavailable"))
    if mode == "http_504":
        return _raise_urlopen(_http_error(504, "Gateway Timeout"))
    if mode == "urlerror":
        return _raise_urlopen(urllib.error.URLError("connection refused"))
    if mode == "timeout":
        return _raise_urlopen(TimeoutError("timed out"))
    if mode == "malformed_json":
        return _ok_urlopen(MALFORMED_FIXTURE.read_bytes())
    raise AssertionError(f"unknown refuse mode: {mode}")


REFUSE_MODES = ("http_503", "http_504", "urlerror", "timeout", "malformed_json")


def _expected_success_doc() -> dict[str, Any]:
    payload = json.loads(SUCCESS_FIXTURE.read_text(encoding="utf-8"))
    row = payload["lines"][0]
    # Reuse the script's existing rounding policy — do not invent another.
    return {
        "sport": "nfl",
        "keiCode": "KEINFL",
        "games": [
            {
                "id": row["game_id"],
                "homeTeam": row["home_team"],
                "awayTeam": row["away_team"],
                "homeAbbr": row["home_abbr"],
                "awayAbbr": row["away_abbr"],
                "commenceTime": row["start_time"],
                "projSpreadHome": round(float(row["spread_home"]), 2),
                "projTotal": round(float(row["total_mean"]), 2),
            }
        ],
    }


def test_source_contract_return_1_before_out_write() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    main_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    try_node = next(node for node in main_fn.body if isinstance(node, ast.Try))
    caught = {
        ast.unparse(elt) if hasattr(ast, "unparse") else None
        for handler in try_node.handlers
        for elt in (
            handler.type.elts
            if isinstance(handler.type, ast.Tuple)
            else [handler.type]
        )
        if handler.type is not None
    }
    assert "urllib.error.URLError" in caught
    assert "TimeoutError" in caught
    assert "json.JSONDecodeError" in caught
    returns = [
        node.value.value
        for handler in try_node.handlers
        for node in handler.body
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant)
    ]
    assert 1 in returns
    try_index = main_fn.body.index(try_node)
    after = main_fn.body[try_index + 1 :]
    write_dump = [
        node
        for node in ast.walk(ast.Module(body=after, type_ignores=[]))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "dump"
    ]
    assert write_dump, "json.dump(OUT) must stay after the refuse return"
    assert "return 1" in src
    assert "json.dump" in src


@pytest.mark.parametrize("mode", REFUSE_MODES)
def test_transport_json_error_returns_1_and_creates_no_out(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    monkeypatch.setattr(mod.urllib.request, "urlopen", _refuse_urlopen(mode))
    monkeypatch.setattr(urllib.request, "urlopen", _refuse_urlopen(mode))

    real_before = REAL_OUT.read_bytes() if REAL_OUT.is_file() else None
    rc = mod.main()

    assert rc == 1
    assert not out.exists()
    assert not out.parent.exists()
    if real_before is None:
        assert not REAL_OUT.exists()
    else:
        assert REAL_OUT.read_bytes() == real_before


@pytest.mark.parametrize("mode", REFUSE_MODES)
def test_transport_json_error_leaves_preexisting_out_bytes_unchanged(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    out.parent.mkdir(parents=True)
    out.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(mod.urllib.request, "urlopen", _refuse_urlopen(mode))

    rc = mod.main()

    assert rc == 1
    assert out.read_bytes() == SENTINEL_BYTES


def test_success_control_writes_existing_schema_and_rounding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unconditional refuse must not pass — real parser/export path runs."""
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    body = SUCCESS_FIXTURE.read_bytes()
    monkeypatch.setattr(mod.urllib.request, "urlopen", _ok_urlopen(body))

    rc = mod.main()

    assert rc == 0
    assert out.is_file()
    raw = out.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    got = json.loads(raw)
    expected = _expected_success_doc()
    assert got == expected
    assert got["games"][0]["projSpreadHome"] == -3.26
    assert got["games"][0]["projTotal"] == 47.55
    assert got["games"][0]["commenceTime"] == "2026-09-10T20:20:00-04:00"
    # Blank-home row is skipped by existing filter — not a refuse.
    assert len(got["games"]) == 1


@pytest.mark.parametrize("mode", REFUSE_MODES)
def test_process_exit_1_on_refuse_modes(mode: str, tmp_path: Path) -> None:
    result, out = _run_as_process(tmp_path, mode=mode, preexisting=None)
    assert result.returncode == 1, result.stderr.decode("utf-8", "replace")
    assert b"Failed to fetch fair-lines" in result.stderr
    assert not out.exists()


@pytest.mark.parametrize("mode", REFUSE_MODES)
def test_process_exit_1_preserves_preexisting_out(mode: str, tmp_path: Path) -> None:
    result, out = _run_as_process(tmp_path, mode=mode, preexisting=SENTINEL_BYTES)
    assert result.returncode == 1, result.stderr.decode("utf-8", "replace")
    assert out.read_bytes() == SENTINEL_BYTES


def test_process_exit_0_success_control(tmp_path: Path) -> None:
    result, out = _run_as_process(tmp_path, mode="success", preexisting=None)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    got = json.loads(out.read_text(encoding="utf-8"))
    assert got == _expected_success_doc()
    assert b"Wrote " in result.stdout
    assert b"KEINFL" in result.stdout


def _run_as_process(
    tmp_path: Path, *, mode: str, preexisting: bytes | None
) -> tuple[subprocess.CompletedProcess[bytes], Path]:
    out = tmp_path / "processed" / "kei_lines_nfl.json"
    if preexisting is not None:
        out.parent.mkdir(parents=True)
        out.write_bytes(preexisting)

    harness = tmp_path / "c10_harness.py"
    harness.write_text(
        _HARNESS_SRC.format(
            script=json.dumps(str(SCRIPT)),
            out=json.dumps(str(out)),
            mode=json.dumps(mode),
            success_path=json.dumps(str(SUCCESS_FIXTURE)),
            malformed_path=json.dumps(str(MALFORMED_FIXTURE)),
            c10_base=json.dumps(C10_BASE),
        ),
        encoding="utf-8",
    )

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        **EXPORT_ENV,
    }
    # Do not forward credential-bearing env into the child.
    result = subprocess.run(
        [sys.executable, str(harness)],
        capture_output=True,
        env=env,
        timeout=15,
        cwd=str(tmp_path),
    )
    return result, out


_HARNESS_SRC = r"""
import importlib.util
import json
import sys
import urllib.error

script = {script}
out = {out}
mode = {mode}
success_path = {success_path}
malformed_path = {malformed_path}
c10_base = {c10_base}

spec = importlib.util.spec_from_file_location("export_kei_lines_nfl_c10_proc", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.OUT = __import__("pathlib").Path(out)


def _ok(body: bytes):
    def _urlopen(url, timeout=None):
        assert str(url).startswith(c10_base), url
        assert timeout == 30
        class _Resp:
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return False
            def read(self):
                return body
        return _Resp()
    return _urlopen


def _raise(exc):
    def _urlopen(url, timeout=None):
        assert str(url).startswith(c10_base), url
        assert timeout == 30
        raise exc
    return _urlopen


def _http(code, msg):
    return urllib.error.HTTPError(
        url=c10_base + "/nfl/fair-lines", code=code, msg=msg, hdrs=None, fp=None
    )

if mode == "success":
    fn = _ok(__import__("pathlib").Path(success_path).read_bytes())
elif mode == "http_503":
    fn = _raise(_http(503, "Service Unavailable"))
elif mode == "http_504":
    fn = _raise(_http(504, "Gateway Timeout"))
elif mode == "urlerror":
    fn = _raise(urllib.error.URLError("connection refused"))
elif mode == "timeout":
    fn = _raise(TimeoutError("timed out"))
elif mode == "malformed_json":
    fn = _ok(__import__("pathlib").Path(malformed_path).read_bytes())
else:
    raise SystemExit("unknown mode")

mod.urllib.request.urlopen = fn
raise SystemExit(mod.main())
"""


def test_http_error_is_urlerror_subclass() -> None:
    """f5e3bb58 catches URLError; HTTP 503/504 ride that branch (not a new rule)."""
    assert issubclass(urllib.error.HTTPError, urllib.error.URLError)


def _is_os_environ(func: ast.AST) -> bool:
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "get"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "environ"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "os"
    )


def test_script_does_not_read_credential_env() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    environ_keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and _is_os_environ(node.func)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            environ_keys.add(node.args[0].value)
    assert environ_keys == set(EXPORT_ENV)
    for secret in CREDENTIAL_ENV_KEYS:
        assert secret not in src
