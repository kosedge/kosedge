from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from src.main import app
from src.routes import nba as nba_routes


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

        if "select active_model_version from nba_model_runtime_state" in sql:
            active = self.state.get("active_model_version")
            if not active:
                return _FakeResult([])
            return _FakeResult([{"active_model_version": active}])

        if "select state_key, active_model_version" in sql:
            if not self.state.get("active_model_version"):
                return _FakeResult([])
            return _FakeResult(
                [
                    {
                        "state_key": "nba_active_model",
                        "active_model_version": self.state["active_model_version"],
                        "previous_model_version": None,
                        "reason": "test",
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )

        if "select count(*) from nba_market_projections" in sql:
            return _FakeResult(scalar=len(self.state.get("projections", [])))

        if "from nba_market_projections" in sql and "select distinct on" in sql:
            return _FakeResult(self.state.get("projections", []))

        if "insert into nba_market_projections" in sql:
            self.state.setdefault("projections", []).append(
                {
                    "game_id": params.get("game_id"),
                    "game_date": date.today(),
                    "start_time": None,
                    "home_team": "Boston Celtics",
                    "away_team": "New York Knicks",
                    "home_win_prob": params.get("home_win_prob"),
                    "fair_home_ml": params.get("fair_home_ml"),
                    "total_mean": params.get("total_mean"),
                    "fair_total": params.get("fair_total"),
                    "fair_spread_home": params.get("fair_spread_home"),
                    "home_cover_prob": params.get("home_cover_prob"),
                    "margin_mean": params.get("margin_mean"),
                    "worker_build_id": params.get("worker_build_id"),
                    "model_version": params.get("model_version"),
                    "projected_at": datetime.now(timezone.utc),
                }
            )
            return _FakeResult([])

        return _FakeResult([])

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_nba_health_and_fair_lines_empty_slate(monkeypatch) -> None:
    state: Dict[str, Any] = {"projections": []}

    def _session_factory() -> _FakeSession:
        return _FakeSession(state)

    monkeypatch.setattr(nba_routes, "SessionLocal", _session_factory)
    client = TestClient(app)

    health = client.get("/nba/health")
    assert health.status_code == 200
    body = health.json()
    assert body["ok"] is True
    assert body["sport"] == "nba"
    assert body["phase"] == "phase0"
    assert "worker_build_id" in body
    assert body["worker_build_id"].startswith("nba-poss-sim-")

    fair = client.get("/nba/fair-lines")
    assert fair.status_code == 200
    payload = fair.json()
    assert payload["count"] == 0
    assert payload["lines"] == []
    assert payload["slate_status"] in {
        "offseason_empty",
        "no_projections_yet",
        "schema_not_ready",
    }
    assert "model_version" in payload
    assert payload["phase"] == "phase0"


def test_nba_fair_lines_shape_with_rows(monkeypatch) -> None:
    state: Dict[str, Any] = {
        "active_model_version": "nba-v1-poss-sim",
        "projections": [
            {
                "game_id": "g1",
                "game_date": date(2026, 10, 22),
                "start_time": datetime(2026, 10, 22, 23, 0, tzinfo=timezone.utc),
                "home_team": "Boston Celtics",
                "away_team": "New York Knicks",
                "home_win_prob": 0.58,
                "fair_home_ml": -138,
                "total_mean": 226.4,
                "fair_total": 226.5,
                "fair_spread_home": -3.5,
                "home_cover_prob": 0.51,
                "margin_mean": 3.4,
                "worker_build_id": "nba-poss-sim-20260731-phase0",
                "model_version": "nba-v1-poss-sim",
                "projected_at": datetime.now(timezone.utc),
            }
        ],
    }

    monkeypatch.setattr(nba_routes, "SessionLocal", lambda: _FakeSession(state))
    client = TestClient(app)
    response = client.get("/nba/fair-lines", params={"game_date": "2026-10-22"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    line = payload["lines"][0]
    assert line["home_team"] == "Boston Celtics"
    assert line["fair_spread_home"] == -3.5
    assert line["fair_total"] == 226.5
    assert isinstance(line["fair_home_ml"], int)


def test_nba_demo_simulation() -> None:
    client = TestClient(app)
    response = client.post(
        "/nba/simulations/demo",
        params={
            "home_team": "Denver Nuggets",
            "away_team": "Phoenix Suns",
            "simulations": 800,
            "seed": 12,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "markets" in body
    assert body["markets"]["fair_total"] > 0
    assert body["worker_build_id"].startswith("nba-poss-sim-")
    assert len(body.get("event_sample") or []) > 0


def test_nba_router_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/nba/health" in paths
    assert "/nba/fair-lines" in paths
    assert "/nba/simulations/demo" in paths
    assert "/api/jobs/run-nba-simulations" in paths
    assert "/api/jobs/pull-nba-context" in paths
