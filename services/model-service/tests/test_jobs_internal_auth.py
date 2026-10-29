"""G-JOBS-UNAUTH: every /api/jobs/* route requires require_kosedge_internal.

No network. Celery send_task is monkeypatched. Route inventory comes from
app.routes so a new job path cannot skip the matrix.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.main import app
from src import main as main_module
from src.ops_auth import require_kosedge_internal


SECRET = "test-internal-secret"
MAIN_PY = Path(__file__).resolve().parents[1] / "src" / "main.py"
OPS_AUTH = Path(__file__).resolve().parents[1] / "src" / "ops_auth.py"
_UNGATED_APP_JOBS = re.compile(r'@app\.(?:get|post)\("/api/jobs')
_PAID_PULLS = (
    "/api/jobs/pull-odds-snapshot",
    "/api/jobs/pull-historical-odds-backfill",
    "/api/jobs/pull-nba-historical-odds-densify",
)

# Dummy query bag covers Query(...) fields on enqueue routes; extras are ignored.
_ENQUEUE_PARAMS = {
    "season": "2026",
    "week": "1",
    "start_date": "2026-01-01",
    "end_date": "2026-01-02",
    "challenger_model_version": "nfl-test-v1",
}


def _job_route_calls() -> List[Tuple[str, str]]:
    calls: List[Tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/jobs"):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            calls.append((route.path, method))
    calls.sort()
    return calls


_JOB_ROUTE_CALLS = _job_route_calls()
_JOB_ROUTE_IDS = [f"{method} {path}" for path, method in _JOB_ROUTE_CALLS]


def _concrete_path(path: str) -> str:
    return path.replace("{task_id}", "dummy-task-id")


def _forbid_send_task(monkeypatch, bucket: list) -> None:
    def _boom(*args, **kwargs):
        bucket.append((args, kwargs))
        raise AssertionError("send_task must not run without internal auth")

    monkeypatch.setattr(main_module.celery_app, "send_task", _boom)


def _hit(client: TestClient, path: str, method: str, headers: dict | None = None):
    return client.request(
        method,
        _concrete_path(path),
        params=_ENQUEUE_PARAMS,
        headers=headers or {},
    )


def test_jobs_router_source_uses_shared_gate() -> None:
    text = MAIN_PY.read_text(encoding="utf-8")
    assert 'prefix="/api/jobs"' in text
    assert "Depends(require_kosedge_internal)" in text
    assert _UNGATED_APP_JOBS.search(text) is None
    ops = OPS_AUTH.read_text(encoding="utf-8")
    assert "hmac.compare_digest" in ops
    assert 'got.encode("utf-8")' in ops
    assert 'expected.encode("utf-8")' in ops


def test_jobs_no_ungated_app_decorator_in_main() -> None:
    text = MAIN_PY.read_text(encoding="utf-8")
    leftover = _UNGATED_APP_JOBS.findall(text)
    assert leftover == []


def test_jobs_route_inventory_covers_paid_pulls() -> None:
    assert len(_JOB_ROUTE_CALLS) >= 40
    paths = {path for path, _method in _JOB_ROUTE_CALLS}
    missing = [path for path in _PAID_PULLS if path not in paths]
    assert missing == [], missing


def test_non_ascii_secret_header_is_401_not_500(monkeypatch) -> None:
    """CPython compare_digest(str, str) TypeError on non-ASCII → must stay 401."""
    from starlette.requests import Request

    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/jobs/pull-odds-snapshot",
        "raw_path": b"/api/jobs/pull-odds-snapshot",
        "query_string": b"",
        "headers": [(b"x-kosedge-secret", b"caf\xe9")],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    request = Request(scope)
    with pytest.raises(HTTPException) as excinfo:
        require_kosedge_internal(request)
    assert excinfo.value.status_code == 401


@pytest.mark.parametrize("path,method", _JOB_ROUTE_CALLS, ids=_JOB_ROUTE_IDS)
def test_jobs_missing_header_is_401_and_never_enqueues(path: str, method: str, monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)
    send_calls: list = []
    _forbid_send_task(monkeypatch, send_calls)
    client = TestClient(app)
    response = _hit(client, path, method)
    assert response.status_code == 401, (path, method, response.status_code, response.text)
    assert send_calls == [], (path, method, send_calls)


@pytest.mark.parametrize("path,method", _JOB_ROUTE_CALLS, ids=_JOB_ROUTE_IDS)
def test_jobs_wrong_header_is_401_and_never_enqueues(path: str, method: str, monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)
    send_calls: list = []
    _forbid_send_task(monkeypatch, send_calls)
    client = TestClient(app)
    response = _hit(client, path, method, headers={"x-kosedge-secret": "wrong-secret"})
    assert response.status_code == 401, (path, method, response.status_code, response.text)
    assert send_calls == [], (path, method, send_calls)


def test_jobs_unset_secret_is_503_and_never_enqueues(monkeypatch) -> None:
    monkeypatch.delenv("INTERNAL_API_SECRET", raising=False)
    send_calls: list = []
    _forbid_send_task(monkeypatch, send_calls)
    client = TestClient(app)
    for path, method in _JOB_ROUTE_CALLS:
        response = _hit(client, path, method, headers={"x-kosedge-secret": SECRET})
        assert response.status_code == 503, (path, method, response.status_code, response.text)
        assert send_calls == [], (path, method, send_calls)


def _is_enqueue_route(path: str, method: str) -> bool:
    if method != "POST":
        return False
    if path.rstrip("/").endswith("/revoke"):
        return False
    return True


def test_jobs_correct_header_enqueues_once(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)
    send_calls: list = []

    class _AsyncResult:
        id = "task-test"

    def _ok(*args, **kwargs):
        send_calls.append((args, kwargs))
        return _AsyncResult()

    monkeypatch.setattr(main_module.celery_app, "send_task", _ok)
    client = TestClient(app)
    headers = {"x-kosedge-secret": SECRET}
    enqueue_routes = [
        (path, method)
        for path, method in _JOB_ROUTE_CALLS
        if _is_enqueue_route(path, method)
    ]
    assert enqueue_routes, "expected enqueue routes from app.routes"
    for path, method in enqueue_routes:
        send_calls.clear()
        response = _hit(client, path, method, headers=headers)
        assert response.status_code == 200, (path, method, response.status_code, response.text)
        assert len(send_calls) == 1, (path, method, send_calls)
        body = response.json()
        assert body.get("task_id") == "task-test", (path, body)
