"""t5178u NFL export policy — no M0 types.

Retains #697 / 0aad8d75 transport refusals (503/504/URLError/Timeout/JSON).
Adds decided policy rows: empty lines, blank identity, nonfinite numeric,
inconsistent counts, honesty-enum empty, 503-shaped error body, preserve
prior OUT, atomic replace. Synthetic urllib + tmp OUT only.

CERT=0. No model/Odds HTTP. No DB. No credential env reads. No thresholds.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = WEB_ROOT / "scripts" / "export_kei_lines_nfl.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "export_kei_t5178u"
SUCCESS_FIXTURE = FIXTURE_DIR / "fair_lines_success.json"
MALFORMED_FIXTURE = FIXTURE_DIR / "malformed.json"
REAL_OUT = WEB_ROOT / "data" / "processed" / "kei_lines_nfl.json"

C10_BASE = "http://c10.test.invalid"
SENTINEL_BYTES = b"PREEXISTING-KEI-T5178U-SENTINEL\n"

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

# Common-sports honest-empty statuses — must NOT become NFL export success.
HONESTY_EMPTY_STATUSES = (
    "not_connected",
    "no_odds_yet",
    "offseason_empty",
    "no_projections_yet",
    "empty",
    "no_slate",
    "preseason_empty",
    "misconfigured",
    "upstream_error",
    "upstream_unreachable",
)

TRANSPORT_MODES = ("http_503", "http_504", "urlerror", "timeout", "malformed_json")


def _load_export_mod():
    spec = importlib.util.spec_from_file_location(
        "export_kei_lines_nfl_t5178u_policy", SCRIPT
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


def _transport_urlopen(mode: str) -> Callable[..., Any]:
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
    raise AssertionError(f"unknown transport mode: {mode}")


def _expected_success_doc() -> dict[str, Any]:
    payload = json.loads(SUCCESS_FIXTURE.read_text(encoding="utf-8"))
    row = payload["lines"][0]
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


def _last_refuse(stderr: str) -> dict[str, Any]:
    lines = [ln for ln in stderr.splitlines() if ln.strip().startswith("{")]
    assert lines, stderr
    doc = json.loads(lines[-1])
    assert doc["ok"] is False
    assert doc["actionable"] is False
    assert doc["sport"] == "nfl"
    assert doc["statusContract"] == "nfl-export-status-v1"
    return doc


def _run_payload(
    mod: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
    *,
    preexisting: bytes | None = None,
) -> tuple[int, Path, str]:
    out = _bind_out(mod, tmp_path)
    if preexisting is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(preexisting)
    body = json.dumps(payload).encode("utf-8")
    monkeypatch.setattr(mod.urllib.request, "urlopen", _ok_urlopen(body))
    cap: list[str] = []
    monkeypatch.setattr(
        sys,
        "stderr",
        type("E", (), {"write": lambda _s, t: cap.append(t), "flush": lambda _s: None})(),
    )
    rc = mod.main()
    return rc, out, "".join(cap)


def test_http_error_is_urlerror_subclass() -> None:
    """#697 0aad8d75: HTTP 503/504 ride the URLError catch."""
    assert issubclass(urllib.error.HTTPError, urllib.error.URLError)


def test_source_retains_transport_catch_return_1() -> None:
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
    assert "return 1" in src
    assert "FAIR_LINES_HONESTY_SPORTS" not in src
    assert "FAIR_LINES_HONEST_EMPTY" not in src
    assert "nfl-export-status-v1" in src


def test_script_does_not_read_credential_env() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    environ_keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "environ"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "os"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            environ_keys.add(node.args[0].value)
    assert environ_keys == set(EXPORT_ENV)
    for secret in CREDENTIAL_ENV_KEYS:
        assert secret not in src


@pytest.mark.parametrize("mode", TRANSPORT_MODES)
def test_transport_refuse_exit_1_creates_no_out(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    monkeypatch.setattr(mod.urllib.request, "urlopen", _transport_urlopen(mode))
    real_before = REAL_OUT.read_bytes() if REAL_OUT.is_file() else None
    rc = mod.main()
    assert rc == 1
    assert not out.exists()
    if real_before is None:
        assert not REAL_OUT.exists() or REAL_OUT.read_bytes() != SENTINEL_BYTES
    else:
        assert REAL_OUT.read_bytes() == real_before


@pytest.mark.parametrize("mode", TRANSPORT_MODES)
def test_transport_refuse_preserves_prior_out(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    out.parent.mkdir(parents=True)
    out.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(mod.urllib.request, "urlopen", _transport_urlopen(mode))
    rc = mod.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert out.read_bytes() == SENTINEL_BYTES
    refuse = _last_refuse(captured.err)
    assert refuse["reason"] == "upstream_unavailable"
    if mode != "malformed_json":
        assert "Failed to fetch fair-lines" in captured.err


def test_http_503_empty_reasons_still_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Alex X2: 503 with empty reasons is unavailable, never exit-0."""
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    out.parent.mkdir(parents=True)
    out.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        _raise_urlopen(_http_error(503, "")),
    )
    rc = mod.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert out.read_bytes() == SENTINEL_BYTES
    refuse = _last_refuse(captured.err)
    assert refuse["reason"] == "upstream_unavailable"
    assert refuse["actionable"] is False


def test_success_atomic_replace_and_rounding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    monkeypatch.setattr(
        mod.urllib.request, "urlopen", _ok_urlopen(SUCCESS_FIXTURE.read_bytes())
    )
    rc = mod.main()
    assert rc == 0
    assert out.is_file()
    raw = out.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    got = json.loads(raw)
    assert got == _expected_success_doc()
    assert got["games"][0]["projSpreadHome"] == -3.26
    assert got["games"][0]["projTotal"] == 47.55
    leftover = list(out.parent.glob(".*.tmp")) + list(out.parent.glob("*.tmp"))
    assert leftover == []


def test_success_replaces_prior_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    out.parent.mkdir(parents=True)
    out.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(
        mod.urllib.request, "urlopen", _ok_urlopen(SUCCESS_FIXTURE.read_bytes())
    )
    rc = mod.main()
    assert rc == 0
    assert out.read_bytes() != SENTINEL_BYTES
    assert json.loads(out.read_text(encoding="utf-8")) == _expected_success_doc()


def test_write_failure_preserves_prior_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    out = _bind_out(mod, tmp_path)
    out.parent.mkdir(parents=True)
    out.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(
        mod.urllib.request, "urlopen", _ok_urlopen(SUCCESS_FIXTURE.read_bytes())
    )

    def _boom(src: object, dst: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(mod.os, "replace", _boom)
    rc = mod.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert out.read_bytes() == SENTINEL_BYTES
    assert _last_refuse(captured.err)["reason"] == "write_failed"
    leftover = list(out.parent.glob(".*.tmp"))
    assert leftover == []


@pytest.mark.parametrize(
    "payload,reason",
    [
        ({}, "unexpected_empty_payload"),
        ({"lines": None}, "unexpected_empty_payload"),
        ({"lines": []}, "unexpected_empty_payload"),
        ({"lines": [], "count": 0}, "unexpected_empty_payload"),
        (
            {"error": "nfl_edge_board_unavailable", "lines": [], "games": 0},
            "upstream_unavailable",
        ),
        (
            {
                "lines": [
                    {
                        "game_id": "g1",
                        "home_team": "   ",
                        "away_team": "Buffalo Bills",
                        "spread_home": -3.0,
                        "total_mean": 44.0,
                    }
                ]
            },
            "blank_required_identity",
        ),
        (
            {
                "lines": [
                    {
                        "game_id": "",
                        "home_team": "Kansas City Chiefs",
                        "away_team": "Buffalo Bills",
                        "spread_home": -3.0,
                        "total_mean": 44.0,
                    }
                ]
            },
            "blank_required_identity",
        ),
        (
            {
                "lines": [
                    {
                        "game_id": "g1",
                        "home_team": "Kansas City Chiefs",
                        "away_team": "Buffalo Bills",
                        "spread_home": "not-a-number",
                        "total_mean": 44.0,
                    }
                ]
            },
            "malformed_numeric",
        ),
        (
            {
                "lines": [
                    {
                        "game_id": "g1",
                        "home_team": "Kansas City Chiefs",
                        "away_team": "Buffalo Bills",
                        "spread_home": "NaN",
                        "total_mean": 44.0,
                    }
                ]
            },
            "malformed_numeric",
        ),
        (
            {
                "count": 2,
                "lines": [
                    {
                        "game_id": "g1",
                        "home_team": "Kansas City Chiefs",
                        "away_team": "Buffalo Bills",
                        "spread_home": -3.0,
                        "total_mean": 44.0,
                    }
                ],
            },
            "inconsistent_counts",
        ),
    ],
)
def test_policy_refuse_nonzero_non_actionable(
    payload: dict[str, Any],
    reason: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    rc, out, err = _run_payload(mod, tmp_path, monkeypatch, payload, preexisting=SENTINEL_BYTES)
    assert rc == 1
    assert out.read_bytes() == SENTINEL_BYTES
    assert _last_refuse(err)["reason"] == reason


@pytest.mark.parametrize("slate_status", HONESTY_EMPTY_STATUSES)
def test_honesty_enum_empty_is_not_nfl_success(
    slate_status: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFL∉HONESTY — common-sports empty statuses are still unexpected empty."""
    _strip_credentials(monkeypatch)
    mod = _load_export_mod()
    rc, out, err = _run_payload(
        mod,
        tmp_path,
        monkeypatch,
        {"lines": [], "slate_status": slate_status, "count": 0},
        preexisting=SENTINEL_BYTES,
    )
    assert rc == 1
    assert out.read_bytes() == SENTINEL_BYTES
    refuse = _last_refuse(err)
    assert refuse["reason"] == "unexpected_empty_payload"
    assert refuse["actionable"] is False


def test_assemble_games_blank_does_not_partial_drop() -> None:
    mod = _load_export_mod()
    with pytest.raises(mod.NflExportRefuse) as caught:
        mod.assemble_games(
            {
                "lines": [
                    {
                        "game_id": "ok",
                        "home_team": "Kansas City Chiefs",
                        "away_team": "Buffalo Bills",
                        "spread_home": -3.0,
                        "total_mean": 44.0,
                    },
                    {
                        "game_id": "bad",
                        "home_team": "",
                        "away_team": "New York Jets",
                        "spread_home": 1.5,
                        "total_mean": 40.0,
                    },
                ]
            }
        )
    assert caught.value.reason == "blank_required_identity"
    assert caught.value.actionable is False


def test_assemble_games_success_matches_rounding() -> None:
    mod = _load_export_mod()
    payload = json.loads(SUCCESS_FIXTURE.read_text(encoding="utf-8"))
    games = mod.assemble_games(payload)
    assert games == _expected_success_doc()["games"]
