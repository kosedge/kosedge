from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from src.main import app
from src.routes import wnba as wnba_routes


class _FakeRow:
    def __init__(self, mapping: Dict[str, Any]) -> None:
        self._mapping = mapping

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self._mapping.values())[key]
        return self._mapping[key]

    def __getattr__(self, name: str) -> Any:
        try:
            return self._mapping[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class _FakeResult:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def fetchone(self) -> Optional[_FakeRow]:
        if self._scalar is not None and not self._rows:
            return _FakeRow({"count": self._scalar})
        if not self._rows:
            return None
        return _FakeRow(self._rows[0])

    def fetchall(self) -> List[_FakeRow]:
        return [_FakeRow(row) for row in self._rows]


class _FakeSession:
    def __init__(self, state: Dict[str, Any]) -> None:
        self.state = state
        self.committed = False

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        params = params or {}

        if "create table if not exists" in sql or "create index if not exists" in sql:
            return _FakeResult([])
        if "alter table" in sql:
            return _FakeResult([])

        if "select active_model_version from wnba_model_runtime_state" in sql:
            active = self.state.get("active_model_version")
            if not active:
                return _FakeResult([])
            return _FakeResult([{"active_model_version": active}])

        if "select count(*) from wnba_market_projections" in sql:
            return _FakeResult(scalar=len(self.state.get("projections", [])))

        if "from wnba_market_projections" in sql and "select distinct on" in sql:
            return _FakeResult(self.state.get("projections", []))

        if "from wnba_player_prop_model_edges" in sql:
            return _FakeResult([])

        if "insert into wnba_market_projections" in sql:
            self.state.setdefault("projections", []).append(params)
            return _FakeResult([])

        return _FakeResult([])

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_wnba_health(monkeypatch) -> None:
    state: Dict[str, Any] = {"projections": []}

    def _session():
        return _FakeSession(state)

    monkeypatch.setattr(wnba_routes, "SessionLocal", _session)
    client = TestClient(app)
    res = client.get("/wnba/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["sport"] == "wnba"
    assert body["default_model_version"] == "wnba-v1-poss-sim"
    assert "worker_build_id" in body
    assert body.get("pace_method") == "harmonic_mean"
    assert body.get("game_minutes") == 40
    assert "schema_ready" in body


def test_wnba_fair_lines_empty_honest(monkeypatch) -> None:
    state: Dict[str, Any] = {"projections": []}

    def _session():
        return _FakeSession(state)

    monkeypatch.setattr(wnba_routes, "SessionLocal", _session)
    client = TestClient(app)
    res = client.get("/wnba/fair-lines")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 0
    assert body["slate_status"] in {
        "offseason_empty",
        "no_projections_yet",
        "schema_not_ready",
    }
    assert body["phase"] == "phase3"


def test_wnba_demo_simulation() -> None:
    client = TestClient(app)
    res = client.post(
        "/wnba/simulations/demo",
        params={"simulations": 500, "seed": 7},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["model_version"] == "wnba-v1-poss-sim"
    assert body["rates"]["pace_method"] == "harmonic_mean"
    assert 0.0 <= body["markets"]["home_win_prob"] <= 1.0


def test_wnba_router_registered() -> None:
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/wnba/health" in paths
    assert "/wnba/fair-lines" in paths
    assert "/wnba/props/board" in paths
    assert "/wnba/ops/inventory" in paths
