from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.main import app
from src.routes import nfl as nfl_routes


class _FakeRow:
    def __init__(self, mapping: Dict[str, Any]) -> None:
        self._mapping = mapping

    def __getattr__(self, name: str) -> Any:
        return self._mapping[name]


class _Result:
    def __init__(self, rows=None, row=None) -> None:
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return [_FakeRow(r) for r in self._rows]

    def fetchone(self):
        return _FakeRow(self._row) if self._row is not None else None


class _Session:
    def __init__(self) -> None:
        self.committed = False

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _Result:
        sql = " ".join(str(statement).split()).lower()
        if "from nfl_player_mapping_review_queue q where q.queue_status" in sql:
            return _Result(
                rows=[
                    {
                        "id": "queue-1",
                        "mapping_event_id": "event-1",
                        "queue_status": "pending",
                        "priority": "high",
                        "reason": "conflict",
                        "observed_source": "odds_api_nfl_props",
                        "observed_external_id": None,
                        "observed_player_name": "Player A",
                        "normalized_name": "player a",
                        "observed_team": "BUF",
                        "observed_position": "WR",
                        "observed_season": 2026,
                        "observed_week": 1,
                        "candidate_player_uids": ["uid-1", "uid-2"],
                        "proposed_player_uid": None,
                        "reviewer": None,
                        "reviewer_notes": None,
                        "approved_player_uid": None,
                        "reviewed_at": None,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_player_mapping_quality_snapshots" in sql:
            return _Result(
                row={
                    "snapshot_date": "2026-09-10",
                    "season": 2026,
                    "week": 1,
                    "resolver_version": "nfl-player-identity-v1",
                    "source_system": "odds_api_nfl_props",
                    "coverage_rate": 0.9,
                    "high_confidence_auto_map_rate": 0.75,
                    "unresolved_rate": 0.05,
                    "conflict_rate": 0.01,
                    "remap_count": 2,
                    "reversal_count": 1,
                    "source_freshness_hours": 4.0,
                    "readiness_status": "go",
                    "metrics": {"mapped_events": 90},
                    "created_at": datetime.now(timezone.utc),
                }
            )
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def test_nfl_identity_endpoints_contract(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Session())
    monkeypatch.setattr(
        nfl_routes,
        "apply_manual_mapping_resolution",
        lambda *_args, **_kwargs: {"updated": True, "status": "approved"},
    )
    monkeypatch.setattr(
        nfl_routes,
        "celery_app",
        SimpleNamespace(send_task=lambda *_args, **_kwargs: SimpleNamespace(id="task-1")),
    )
    client = TestClient(app)

    queue = client.get("/nfl/identity/queue")
    assert queue.status_code == 200
    assert queue.json()["count"] == 1

    action = client.post(
        "/nfl/identity/queue/queue-1/action",
        params={"action": "approve", "reviewer": "ops", "player_uid": "uid-1"},
    )
    assert action.status_code == 200
    assert action.json()["queue_status"] == "approved"

    refresh = client.post("/nfl/identity/refresh", params={"season": 2026, "week": 1, "model_version": "nfl-player-v1"})
    assert refresh.status_code == 200
    assert refresh.json()["task_id"] == "task-1"

    quality = client.get("/nfl/identity/quality/latest", params={"season": 2026, "week": 1})
    assert quality.status_code == 200
    assert quality.json()["snapshot"]["readiness_status"] in {"go", "warning", "no-go"}
