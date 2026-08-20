"""Worker hygiene: no week-22 default remat, remats on models, beat cannot re-poison."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi.testclient import TestClient

from src.celery_app import QUEUE_MODELS, celery_app, celery_healthcheck
from src.celerybeat_schedule import NFL_PLAYER_CYCLE_WEEK, beat_schedule
from src.main import app
from src.nfl_remat_policy import (
    NFL_MODELS_QUEUE_TASKS,
    clamp_cycle_week,
    decode_celery_message,
    is_poison_remat,
    redact_broker_url,
    resolve_remat_weeks,
)
from src.routes import nfl as nfl_routes
from src.tasks import run_nfl_props_layer_rebuild


def test_season_only_remat_weeks_are_regular_season() -> None:
    assert resolve_remat_weeks() == list(range(1, 19))
    assert resolve_remat_weeks(week=None, weeks=None) == list(range(1, 19))
    assert resolve_remat_weeks(week=7) == [7]
    assert resolve_remat_weeks(weeks=[22]) == [22]
    assert resolve_remat_weeks(weeks=[3, 1, 2]) == [1, 2, 3]


def test_cycle_week_clamped_off_week_22() -> None:
    assert clamp_cycle_week(22) == 18
    assert clamp_cycle_week(0) == 1
    assert clamp_cycle_week("9") == 9
    assert NFL_PLAYER_CYCLE_WEEK <= 18


def test_poison_detector_flags_bare_and_week22_rebuild() -> None:
    assert is_poison_remat({"task": "src.tasks.run_nfl_props_layer_rebuild", "kwargs": {}})
    assert is_poison_remat(
        {"task": "src.tasks.run_nfl_props_layer_rebuild", "kwargs": {"season": 2025}}
    )
    assert is_poison_remat(
        {
            "task": "src.tasks.run_nfl_props_layer_rebuild",
            "kwargs": {"season": 2025, "weeks": [22]},
        }
    )
    assert is_poison_remat(
        {
            "task": "src.tasks.materialize_nfl_player_baseline_projections",
            "kwargs": {"season": 2025},
        }
    )
    assert not is_poison_remat(
        {
            "task": "src.tasks.run_nfl_props_layer_rebuild",
            "kwargs": {"season": 2025, "weeks": list(range(1, 19))},
        }
    )


def test_decode_kwargsrepr_bare_rebuild() -> None:
    info = decode_celery_message(
        {
            "headers": {
                "task": "src.tasks.run_nfl_props_layer_rebuild",
                "id": "abc",
                "kwargsrepr": "{'season': 2025}",
            }
        }
    )
    assert info["task"].endswith("run_nfl_props_layer_rebuild")
    assert is_poison_remat(info)


def test_beat_never_schedules_bare_remat_class() -> None:
    tasks = {entry["task"] for entry in beat_schedule.values()}
    assert "src.tasks.run_nfl_props_layer_rebuild" not in tasks
    assert "src.tasks.materialize_nfl_player_baseline_projections" not in tasks
    for name, entry in beat_schedule.items():
        if "nfl" not in name.lower() and "nfl" not in str(entry.get("task", "")).lower():
            continue
        kwargs = entry.get("kwargs") or {}
        if "week" in kwargs:
            assert 1 <= int(kwargs["week"]) <= 18, name
    # Nowcast may be omitted when MLB_NOWCAST_ENABLED=false; default import keeps it.


def test_nfl_remat_tasks_route_to_models_queue() -> None:
    routes = celery_app.conf.task_routes
    for name in NFL_MODELS_QUEUE_TASKS:
        assert routes[name]["queue"] == QUEUE_MODELS
    assert routes["src.tasks.run_nfl_props_layer_rebuild"]["queue"] == QUEUE_MODELS


def test_rebuild_task_expands_bare_season(monkeypatch) -> None:
    calls: list[tuple[str, int | None]] = []

    monkeypatch.setattr(
        "src.tasks.materialize_nfl_player_projection_features_task",
        lambda **kw: {"feature_rows": 0, "week": kw.get("week")},
    )
    monkeypatch.setattr(
        "src.tasks.materialize_nfl_player_baseline_projections",
        lambda **kw: calls.append(("baseline", kw.get("week"))) or {"ok": True},
    )
    monkeypatch.setattr("src.tasks.materialize_nfl_player_box_score_sims", lambda **kw: {"ok": True})
    monkeypatch.setattr("src.tasks.materialize_nfl_player_props_edges", lambda **kw: {"ok": True})

    class _Session:
        def execute(self, *_a, **_k):
            return SimpleNamespace(scalar_one=lambda: 0)

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.tasks.SessionLocal", lambda: _Session())
    out = run_nfl_props_layer_rebuild(season=2025)
    assert out["weeks"] == list(range(1, 19))
    assert [w for kind, w in calls if kind == "baseline"] == list(range(1, 19))


def test_healthcheck_redacts_broker_password() -> None:
    hidden = redact_broker_url("redis://default:supersecret@redis.example:6379/0")
    assert "supersecret" not in hidden
    assert "***" in hidden
    payload = celery_healthcheck()
    blob = str(payload.get("broker") or "")
    assert ":***@" in blob or blob in {"unset", "redacted"} or "@" not in blob or "***" in blob


def test_weekly_fantasy_rankings_empty_on_sql_error(monkeypatch) -> None:
    from sqlalchemy.exc import ProgrammingError

    class _Boom:
        def execute(self, *_a, **_k):
            raise ProgrammingError("SELECT", {}, Exception("ambiguous"))

        def close(self) -> None:
            return None

    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Boom())
    client = TestClient(app)
    response = client.get("/nfl/fantasy/rankings", params={"season": 2026, "week": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["status"] == "empty"
    assert body["rows"] == []


def test_live_flag_is_true_with_honesty_copy() -> None:
    web = Path(__file__).resolve().parents[3] / "apps" / "web" / "lib" / "nfl-weekly-props-live.ts"
    text = web.read_text(encoding="utf-8")
    assert "export const NFL_WEEKLY_PROPS_LIVE = true" in text
    assert "2026 preseason" in text
