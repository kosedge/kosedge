"""Week-1-only in-process props remat — no Celery enqueue."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.main import app
import src.routes.nfl as nfl_routes


OPS_PATH = "/nfl/ops/materialize-player-props-in-process"
SECRET = "test-internal-secret"


def _client(monkeypatch, *, materialize_calls: list, enqueue_calls: list) -> TestClient:
    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)

    def _materialize(**kwargs):
        materialize_calls.append(kwargs)
        return {"ok": True, "upserted": 42, "week": kwargs.get("week"), "season": kwargs.get("season")}

    def _send(*_a, **_kw):
        enqueue_calls.append(("send_task", _a, _kw))
        raise AssertionError("send_task must not be called for in-process remat")

    def _enqueue(*_a, **_kw):
        enqueue_calls.append(("_enqueue_models", _a, _kw))
        raise AssertionError("_enqueue_models must not be called for in-process remat")

    monkeypatch.setattr(
        "src.tasks.materialize_nfl_player_props_edges",
        _materialize,
    )
    monkeypatch.setattr(nfl_routes, "celery_app", SimpleNamespace(send_task=_send))
    monkeypatch.setattr(nfl_routes, "_enqueue_models", _enqueue)
    return TestClient(app)


def test_in_process_week1_succeeds_without_celery(monkeypatch) -> None:
    materialize_calls: list = []
    enqueue_calls: list = []
    client = _client(monkeypatch, materialize_calls=materialize_calls, enqueue_calls=enqueue_calls)

    resp = client.post(
        OPS_PATH,
        params={"season": 2026, "week": 1, "model_version": "nfl-player-v1"},
        headers={"x-kosedge-secret": SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "in_process"
    assert body["week"] == 1
    assert body["weeks"] == [1]
    assert body["queue"] is None
    assert body["result"]["upserted"] == 42
    assert materialize_calls == [
        {"season": 2026, "week": 1, "model_version": "nfl-player-v1"}
    ]
    assert enqueue_calls == []


def test_in_process_weeks_equals_1_succeeds(monkeypatch) -> None:
    materialize_calls: list = []
    enqueue_calls: list = []
    client = _client(monkeypatch, materialize_calls=materialize_calls, enqueue_calls=enqueue_calls)

    resp = client.post(
        OPS_PATH,
        params={"season": 2026, "weeks": "1"},
        headers={"x-kosedge-secret": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["week"] == 1
    assert materialize_calls[0]["week"] == 1
    assert enqueue_calls == []


def test_in_process_bare_season_is_400(monkeypatch) -> None:
    materialize_calls: list = []
    enqueue_calls: list = []
    client = _client(monkeypatch, materialize_calls=materialize_calls, enqueue_calls=enqueue_calls)

    resp = client.post(
        OPS_PATH,
        params={"season": 2026},
        headers={"x-kosedge-secret": SECRET},
    )
    assert resp.status_code == 400
    assert "bare season" in resp.json()["detail"].lower() or "required" in resp.json()["detail"].lower()
    assert materialize_calls == []
    assert enqueue_calls == []


def test_in_process_weeks_1_2_is_400(monkeypatch) -> None:
    materialize_calls: list = []
    enqueue_calls: list = []
    client = _client(monkeypatch, materialize_calls=materialize_calls, enqueue_calls=enqueue_calls)

    resp = client.post(
        OPS_PATH,
        params={"season": 2026, "weeks": "1,2"},
        headers={"x-kosedge-secret": SECRET},
    )
    assert resp.status_code == 400
    assert materialize_calls == []
    assert enqueue_calls == []


def test_in_process_week_22_is_400(monkeypatch) -> None:
    materialize_calls: list = []
    enqueue_calls: list = []
    client = _client(monkeypatch, materialize_calls=materialize_calls, enqueue_calls=enqueue_calls)

    resp = client.post(
        OPS_PATH,
        params={"season": 2026, "week": 22},
        headers={"x-kosedge-secret": SECRET},
    )
    assert resp.status_code == 400
    assert materialize_calls == []
    assert enqueue_calls == []


def test_in_process_requires_internal_auth(monkeypatch) -> None:
    materialize_calls: list = []
    enqueue_calls: list = []
    client = _client(monkeypatch, materialize_calls=materialize_calls, enqueue_calls=enqueue_calls)

    missing = client.post(OPS_PATH, params={"season": 2026, "week": 1})
    assert missing.status_code == 401
    assert materialize_calls == []
    assert enqueue_calls == []


def test_existing_rebuild_props_layers_still_enqueues_models(monkeypatch) -> None:
    """Celery rebuild path unchanged — still models queue."""
    sent: list[tuple[str, dict]] = []

    class _AsyncResult:
        id = "task-rebuild-unchanged"

    def _send(name, kwargs=None, **kw):
        sent.append((name, kwargs or {}, kw))
        return _AsyncResult()

    monkeypatch.setattr(nfl_routes, "celery_app", SimpleNamespace(send_task=_send))
    client = TestClient(app)
    rebuild = client.post(
        "/nfl/ops/rebuild-props-layers",
        params={"season": 2026, "weeks": "1"},
    )
    assert rebuild.status_code == 200
    assert rebuild.json()["task_name"] == "src.tasks.run_nfl_props_layer_rebuild"
    assert rebuild.json()["queue"] == "models"
    assert sent[-1][0] == "src.tasks.run_nfl_props_layer_rebuild"
    assert sent[-1][1]["weeks"] == [1]
