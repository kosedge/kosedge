from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.main import app
from src import main as main_module
from src.routes import nfl as nfl_routes


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
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None) -> None:
        self._rows = rows or []

    def fetchone(self) -> Optional[_FakeRow]:
        if not self._rows:
            return None
        return _FakeRow(self._rows[0])

    def fetchall(self) -> List[_FakeRow]:
        return [_FakeRow(row) for row in self._rows]


class _HealthConn:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        if "from nfl_model_quality_snapshots" in sql:
            return _FakeResult(self._rows)
        raise AssertionError(f"Unexpected SQL in NFL health test: {sql}")


class _HealthEngine:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows

    class _Ctx:
        def __init__(self, rows: List[Dict[str, Any]]) -> None:
            self._conn = _HealthConn(rows)

        def __enter__(self) -> _HealthConn:
            return self._conn

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def connect(self) -> "_HealthEngine._Ctx":
        return _HealthEngine._Ctx(self._rows)


class _NflRouteSession:
    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        if "from nfl_model_backtest_runs" in sql:
            return _FakeResult(
                [
                    {
                        "run_date": date.today().isoformat(),
                        "model_version": "nfl-v1.5-matchup-sim",
                        "payload": {
                            "fold_count": 3,
                            "sample_size": 84,
                            "base_brier_ml": 0.2381,
                            "calibrated_brier_ml": 0.2312,
                            "brier_improvement": 0.0069,
                            "base_mae_total_runs": 5.8,
                            "calibrated_mae_total_runs": 5.8,
                            "mae_improvement": 0.0,
                            "leakage_violations": 0,
                            "folds": [{"test_start": "2026-09-01", "test_end": "2026-09-07"}],
                        },
                        "created_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_market_projections np" in sql:
            return _FakeResult(
                [
                    {
                        "game_id": "g-good",
                        "home_team": "Buffalo Bills",
                        "away_team": "Miami Dolphins",
                        "home_win_prob": 0.71,
                        "total_mean": 47.8,
                        "projection": {"markets": {"total_p10": 42.0, "total_p90": 51.5}},
                        "created_at": datetime.now(timezone.utc),
                    },
                    {
                        "game_id": "g-low",
                        "home_team": "New York Jets",
                        "away_team": "New England Patriots",
                        "home_win_prob": 0.51,
                        "total_mean": 42.2,
                        "projection": {"markets": {"total_p10": 33.0, "total_p90": 53.5}},
                        "created_at": datetime.now(timezone.utc),
                    },
                ]
            )
        if "from nfl_model_quality_snapshots" in sql:
            return _FakeResult(
                [
                    {
                        "payload": {
                            "moneyline_brier": 0.23,
                            "total_mae": 5.4,
                            "clv_avg": 0.01,
                        }
                    }
                ]
            )
        raise AssertionError(f"Unexpected SQL in NFL route test: {sql}")

    def close(self) -> None:
        return None


def test_nfl_backtest_report_endpoint_shape(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    response = client.get("/nfl/ops/backtest-report")
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "nfl-v1.5-matchup-sim"
    assert "fold_count" in payload["report"]["summary"]
    assert "brier_improvement" in payload["report"]["summary"]
    assert isinstance(payload["report"]["folds"], list)


def test_nfl_health_readiness_go_and_no_go(monkeypatch) -> None:
    good_snapshot = [
        {
            "run_date": date.today().isoformat(),
            "payload": {
                "sample_size": 180,
                "calendar_days_covered": 21,
                "last_game_date": date.today().isoformat(),
                "moneyline_brier": 0.23,
                "total_mae": 5.4,
                "clv_avg": 0.009,
            },
            "created_at": datetime.now(timezone.utc),
        }
    ]
    monkeypatch.setattr(main_module, "engine", _HealthEngine(good_snapshot))
    client = TestClient(app)
    go = client.get("/health/nfl-production-readiness")
    assert go.status_code == 200
    assert go.json()["status"] == "go"

    bad_snapshot = [
        {
            "run_date": date.today().isoformat(),
            "payload": {
                "sample_size": 180,
                "calendar_days_covered": 21,
                "last_game_date": date.today().isoformat(),
                "moneyline_brier": 0.41,
                "total_mae": 8.8,
                "clv_avg": -0.02,
            },
            "created_at": datetime.now(timezone.utc),
        }
    ]
    monkeypatch.setattr(main_module, "engine", _HealthEngine(bad_snapshot))
    no_go = client.get("/health/nfl-production-readiness")
    assert no_go.status_code == 503
    detail = no_go.json()["detail"]
    assert detail["status"] == "no-go"
    assert detail["gating_checks"]["moneyline_brier_ok"] is False


def test_nfl_readiness_production_mode_keeps_strict_freshness(monkeypatch) -> None:
    stale_snapshot = [
        {
            "run_date": date.today().isoformat(),
            "payload": {
                "sample_size": 180,
                "calendar_days_covered": 21,
                "last_game_date": (date.today() - timedelta(days=40)).isoformat(),
                "moneyline_brier": 0.23,
                "total_mae": 5.4,
                "clv_avg": 0.009,
            },
            "created_at": datetime.now(timezone.utc),
        }
    ]
    monkeypatch.setenv("NFL_READINESS_MODE", "production")
    monkeypatch.setenv("NFL_READINESS_STAGING_MAX_LAST_GAME_AGE_DAYS", "120")
    monkeypatch.setattr(main_module, "engine", _HealthEngine(stale_snapshot))
    client = TestClient(app)
    response = client.get("/health/nfl-production-readiness")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["gating_checks"]["freshness_ok"] is False
    assert detail["freshness_policy"]["mode"] == "production"
    assert detail["freshness_policy"]["override_active"] is False
    assert detail["freshness_policy"]["max_last_game_age_days_applied"] == 8


def test_nfl_readiness_staging_override_relaxes_freshness(monkeypatch) -> None:
    stale_snapshot = [
        {
            "run_date": date.today().isoformat(),
            "payload": {
                "sample_size": 180,
                "calendar_days_covered": 21,
                "last_game_date": (date.today() - timedelta(days=40)).isoformat(),
                "moneyline_brier": 0.23,
                "total_mae": 5.4,
                "clv_avg": 0.009,
            },
            "created_at": datetime.now(timezone.utc),
        }
    ]
    monkeypatch.setenv("NFL_READINESS_MODE", "staging")
    monkeypatch.setenv("NFL_READINESS_STAGING_MAX_LAST_GAME_AGE_DAYS", "120")
    monkeypatch.setattr(main_module, "engine", _HealthEngine(stale_snapshot))
    client = TestClient(app)
    response = client.get("/health/nfl-production-readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "go"
    assert payload["gating_checks"]["freshness_ok"] is True
    assert payload["freshness_policy"]["mode"] == "staging"
    assert payload["freshness_policy"]["override_active"] is True
    assert payload["freshness_policy"]["max_last_game_age_days_applied"] == 120


def test_nfl_edges_today_filters_low_confidence(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    monkeypatch.setattr(
        nfl_routes,
        "fetch_odds",
        lambda **_kwargs: [
            {
                "home_team": "Buffalo Bills",
                "away_team": "Miami Dolphins",
                "bookmakers": [
                    {
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Buffalo Bills", "price": -130},
                                    {"name": "Miami Dolphins", "price": 112},
                                ],
                            },
                            {
                                "key": "totals",
                                "outcomes": [{"name": "Over", "point": 47.5, "price": -110}],
                            },
                        ]
                    }
                ],
            },
            {
                "home_team": "New York Jets",
                "away_team": "New England Patriots",
                "bookmakers": [
                    {
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "New York Jets", "price": -108},
                                    {"name": "New England Patriots", "price": -102},
                                ],
                            },
                            {
                                "key": "totals",
                                "outcomes": [{"name": "Over", "point": 42.5, "price": -110}],
                            },
                        ]
                    }
                ],
            },
        ],
    )
    client = TestClient(app)
    response = client.get(
        "/nfl/edges/today",
        params={
            "model_version": "nfl-v1.5-matchup-sim",
            "min_quality_score": 0,
            "min_confidence_score": 0.3,
            "min_ml_edge_prob": 0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["edges"][0]["game_id"] == "g-good"
    assert payload["diagnostics"]["filtered_count"] == 1
    assert payload["diagnostics"]["filtered_reasons"]["confidence_score"] == 1


def test_nfl_walkforward_job_endpoint_shape(monkeypatch) -> None:
    class _AsyncResult:
        id = "task-123"

    monkeypatch.setattr(main_module.celery_app, "send_task", lambda *_args, **_kwargs: _AsyncResult())
    client = TestClient(app)
    response = client.post("/api/jobs/run-nfl-walkforward-backtest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task-123"
    assert payload["task_name"] == "src.tasks.run_nfl_walkforward_backtest"
