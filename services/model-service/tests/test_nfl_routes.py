from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError

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

    def scalar_one(self) -> Any:
        row = self.fetchone()
        if row is None:
            raise AssertionError("Expected scalar row but none found")
        return row[0]

    def scalar_one_or_none(self) -> Any:
        row = self.fetchone()
        if row is None:
            return None
        return row[0]

    class _ScalarResult:
        def __init__(self, rows: List[Dict[str, Any]]) -> None:
            self._rows = rows

        def all(self) -> List[Any]:
            values: List[Any] = []
            for row in self._rows:
                if row:
                    values.append(next(iter(row.values())))
            return values

    def scalars(self) -> "_FakeResult._ScalarResult":
        return _FakeResult._ScalarResult(self._rows)


class _HealthConn:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        if "from nfl_model_quality_snapshots" in sql:
            return _FakeResult(self._rows)
        if "from nfl_decomposition_drift_snapshots" in sql:
            return _FakeResult([])
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
        params = params or {}
        requested_season = params.get("season")
        requested_week = params.get("week")
        if "select to_regclass" in sql:
            qualified = str(params.get("qualified_name") or "")
            return _FakeResult([{"to_regclass": qualified or "public.unknown"}])
        if "from nfl_dp_team_situational_weekly" in sql and "order by case when team_count >= 16" in sql:
            if requested_season == 2026:
                return _FakeResult([{"season": 2026, "week": 7, "row_count": 32, "team_count": 32}])
            return _FakeResult([{"season": 2025, "week": 22, "row_count": 320, "team_count": 32}])
        if "from nfl_dp_standings_weekly" in sql and "order by case when team_count >= 16" in sql:
            if requested_season == 2026:
                return _FakeResult([{"season": 2026, "week": 7, "row_count": 32, "team_count": 32}])
            return _FakeResult([{"season": 2025, "week": 22, "row_count": 320, "team_count": 32}])
        if "from nfl_dp_depth_chart_weekly" in sql and "order by case when team_count >= 16" in sql:
            if requested_season == 2026:
                return _FakeResult([{"season": 2026, "week": 7, "row_count": 1280, "team_count": 32}])
            return _FakeResult([{"season": 2025, "week": 22, "row_count": 1240, "team_count": 32}])
        if "from nfl_dp_injuries" in sql and "order by case when team_count >= 16" in sql:
            if requested_season == 2026:
                return _FakeResult([{"season": 2026, "week": 7, "row_count": 210, "team_count": 32}])
            return _FakeResult([{"season": 2025, "week": 22, "row_count": 240, "team_count": 32}])
        if "with season_availability as (" in sql and "from nfl_dp_rosters" in sql:
            if requested_season == 2026:
                return _FakeResult([{"season": 2026, "row_count": 1700, "team_count": 32}])
            return _FakeResult([{"season": 2025, "row_count": 1690, "team_count": 32}])
        if (
            "with availability as (" in sql
            and "where season = :season" in sql
            and "and week = :week" in sql
            and "count(*)::int as row_count" in sql
        ):
            has_data = requested_season == 2026 and requested_week == 7
            return _FakeResult(
                [
                    {
                        "season": requested_season,
                        "week": requested_week,
                        "row_count": 32 if has_data else 0,
                        "team_count": 32 if has_data else 0,
                    }
                ]
            )
        if "from nfl_dp_rosters" in sql and "where season = :season" in sql and "count(*)::int as row_count" in sql:
            has_data = requested_season in {2025, 2026}
            return _FakeResult(
                [
                    {
                        "season": requested_season,
                        "row_count": 1690 if has_data else 0,
                        "team_count": 32 if has_data else 0,
                    }
                ]
            )
        if "from nfl_dp_rosters" in sql and "group by source" in sql:
            return _FakeResult([{"source": "nfl_com", "row_count": 900}, {"source": "nflverse", "row_count": 790}])
        if (
            "from nfl_dp_team_situational_weekly" in sql
            and "count(*)::int as row_count" in sql
            and ("group by source" in sql or "group by 1" in sql)
        ):
            return _FakeResult([{"source": "nfl_com", "row_count": 28}, {"source": "nflverse", "row_count": 4}])
        if "from nfl_dp_standings_weekly" in sql and "group by source" in sql:
            return _FakeResult([{"source": "nfl_com", "row_count": 32}])
        if "from nfl_dp_injuries" in sql and "group by source" in sql:
            return _FakeResult([{"source": "nflverse", "row_count": 240}])
        if "from standings order by" in sql and "from nfl_dp_standings_weekly" in sql:
            if requested_season == 2026 and requested_week == 1:
                return _FakeResult([])
            return _FakeResult(
                [
                    {
                        "season": requested_season or 2025,
                        "week": requested_week or 22,
                        "team": "BUF",
                        "wins": 6,
                        "losses": 1,
                        "ties": 0,
                        "points_for": 197,
                        "points_against": 151,
                        "point_diff": 46,
                        "win_pct": 0.8571,
                        "conference": "AFC",
                        "division": "East",
                        "conference_wins": None,
                        "conference_losses": None,
                        "conference_ties": None,
                        "conference_pct": None,
                        "division_wins": None,
                        "division_losses": None,
                        "division_ties": None,
                        "division_pct": None,
                    },
                    {
                        "season": requested_season or 2025,
                        "week": requested_week or 22,
                        "team": "NE",
                        "wins": 5,
                        "losses": 2,
                        "ties": 0,
                        "points_for": 151,
                        "points_against": 145,
                        "point_diff": 6,
                        "win_pct": 0.7143,
                        "conference": "AFC",
                        "division": "East",
                        "conference_wins": None,
                        "conference_losses": None,
                        "conference_ties": None,
                        "conference_pct": None,
                        "division_wins": None,
                        "division_losses": None,
                        "division_ties": None,
                        "division_pct": None,
                    },
                ]
            )
        if "from nfl_dp_depth_chart_weekly" in sql:
            if requested_season == 2026 and requested_week == 1:
                return _FakeResult([])
            return _FakeResult(
                [
                    {
                        "season": requested_season or 2025,
                        "week": requested_week or 22,
                        "team": "BUF",
                        "position": "QB",
                        "depth_slot": "starter",
                        "depth_order": 1,
                        "player_uid": None,
                        "player_id": "qb-1",
                        "player_name": "Starter QB",
                        "role_confidence": 0.92349,
                        "inferred_source": "v1_usage_roster_injury",
                    }
                ]
            )
        if "from nfl_dp_injuries" in sql and "order by team, report_status" in sql:
            if requested_season == 2026 and requested_week == 1:
                return _FakeResult([])
            return _FakeResult(
                [
                    {
                        "season": requested_season or 2025,
                        "week": requested_week or 22,
                        "team": "BUF",
                        "player_key": "qb-1",
                        "player_id": "qb-1",
                        "player_name": "Starter QB",
                        "report_status": "Questionable",
                        "practice_status": "Limited",
                        "injury": "Shoulder",
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_dp_rosters r" in sql:
            if requested_season == 2026 and requested_week == 1:
                return _FakeResult([])
            return _FakeResult(
                [
                    {
                        "season": requested_season or 2025,
                        "week": requested_week or 22,
                        "team": "BUF",
                        "player_id": "qb-1",
                        "player_name": "Starter QB",
                        "position": "QB",
                        "jersey_number": "17",
                        "roster_source": "nfl_com",
                        "depth_slot": "starter",
                        "depth_order": 1,
                        "role_confidence": 0.92349,
                        "report_status": "Questionable",
                        "practice_status": "Limited",
                        "injury": "Shoulder",
                        "injury_source": "nflverse",
                    }
                ]
            )
        if "from nfl_dp_team_situational_weekly t" in sql:
            if requested_season == 2026 and requested_week == 1:
                return _FakeResult([])
            return _FakeResult(
                [
                    {
                        "season": requested_season or 2025,
                        "week": requested_week or 22,
                        "team": "BUF",
                        "games_played": 7,
                        "offensive_plays": 452,
                        "defensive_plays": 428,
                        "pass_rate": 0.59123,
                        "early_down_pass_rate": 0.52367,
                        "red_zone_td_rate": 0.64129,
                        "pressure_rate_allowed": 0.21456,
                        "pressure_rate_generated": 0.27991,
                        "success_rate_offense": 0.47211,
                        "success_rate_defense_allowed": 0.40994,
                        "epa_per_play_offense": 0.11389,
                        "epa_per_play_defense_allowed": -0.04376,
                        "stats_source": "nfl_com",
                        "wins": 6,
                        "losses": 1,
                        "ties": 0,
                        "points_for": 197,
                        "points_against": 151,
                        "point_diff": 46,
                        "win_pct": 0.8571,
                        "standings_source": "nfl_com",
                    }
                ]
            )
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
                        "start_time": datetime.now(timezone.utc),
                        "home_team": "Buffalo Bills",
                        "away_team": "Miami Dolphins",
                        "home_win_prob": 0.71,
                        "total_mean": 47.8,
                        "projection": {
                            "markets": {"total_p10": 42.0, "total_p90": 51.5},
                            "diagnostics": {
                                "injury_nowcast": {
                                    "home_freshness_hours": 20.0,
                                    "away_freshness_hours": 21.0,
                                }
                            },
                            "decomposition": {
                                "framework_version": "nfl-handicap-core-v1",
                                "confidence_score": 0.74,
                                "factor_coverage": 0.71,
                                "uncertainty_penalties": {"total_penalty": 0.13},
                                "factor_contributions": {
                                    "base_efficiency": {"margin_points": 2.1, "total_points": 1.4, "available": True}
                                },
                            },
                        },
                        "created_at": datetime.now(timezone.utc),
                    },
                    {
                        "game_id": "g-low",
                        "start_time": datetime.now(timezone.utc),
                        "home_team": "New York Jets",
                        "away_team": "New England Patriots",
                        "home_win_prob": 0.51,
                        "total_mean": 42.2,
                        "projection": {
                            "markets": {"total_p10": 33.0, "total_p90": 53.5},
                            "diagnostics": {
                                "injury_nowcast": {
                                    "home_freshness_hours": 110.0,
                                    "away_freshness_hours": 102.0,
                                }
                            },
                            "decomposition": {
                                "framework_version": "nfl-handicap-core-v1",
                                "confidence_score": 0.22,
                                "factor_coverage": 0.44,
                                "uncertainty_penalties": {"total_penalty": 0.41},
                                "factor_contributions": {
                                    "base_efficiency": {"margin_points": 0.2, "total_points": -0.1, "available": True}
                                },
                            },
                        },
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
        if "from nfl_framework_tuning_runs" in sql:
            return _FakeResult(
                [
                    {
                        "id": "run-1",
                        "run_date": date.today().isoformat(),
                        "model_version": "nfl-v1.5-matchup-sim",
                        "payload": {"status": "ok", "candidate_count": 24},
                        "selected_config": {"guardrails": {"min_ml_edge_prob": 0.01}},
                        "created_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_framework_tuning_candidates" in sql:
            return _FakeResult(
                [
                    {
                        "rank": 1,
                        "score": 0.77,
                        "metrics": {"moneyline_brier": 0.23},
                        "candidate": {"weight_scales": {"base_efficiency_margin_scale": 1.0}},
                        "config_overrides": {"guardrails": {"min_ml_edge_prob": 0.01}},
                        "is_recommended": True,
                    }
                ]
            )
        if "from nfl_decomposition_drift_snapshots" in sql:
            return _FakeResult(
                [
                    {
                        "snapshot_date": date.today().isoformat(),
                        "model_version": "nfl-v1.5-matchup-sim",
                        "status": "warning",
                        "payload": {"top_shifts": [{"factor": "travel_schedule", "relative_shift": 0.22}]},
                        "created_at": datetime.now(timezone.utc),
                    }
                ]
            )
        raise AssertionError(f"Unexpected SQL in NFL route test: {sql}")

    def close(self) -> None:
        return None


class _MissingIntelTableSession(_NflRouteSession):
    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        params = params or {}
        if "select to_regclass" in sql:
            qualified = str(params.get("qualified_name") or "")
            if qualified.endswith("nfl_dp_standings_weekly"):
                return _FakeResult([{"to_regclass": None}])
            return _FakeResult([{"to_regclass": qualified or "public.unknown"}])
        if "from nfl_dp_standings_weekly" in sql:
            raise ProgrammingError(str(statement), params, Exception('relation "nfl_dp_standings_weekly" does not exist'))
        return super().execute(statement, params)


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
    fetch_calls = []

    def _fake_fetch_odds(**kwargs):
        fetch_calls.append(kwargs)
        return [
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
        ]

    monkeypatch.setattr(
        nfl_routes,
        "fetch_odds",
        _fake_fetch_odds,
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
    assert payload["edges"][0]["framework_version"] == "nfl-handicap-core-v1"
    assert "decomposition" in payload["edges"][0]
    assert payload["edges"][0]["guardrails"]["eligible"] is True
    assert payload["diagnostics"]["filtered_count"] == 1
    assert payload["diagnostics"]["filtered_reasons"]["confidence_score"] == 1
    assert payload["diagnostics"]["filtered_reason_codes"]["confidence_score_below_threshold"] == 1
    assert payload["diagnostics"]["bookmakers"] == ["draftkings"]
    assert payload["framework"]["version"] == "nfl-handicap-core-v1"
    assert fetch_calls[0]["params"]["bookmakers"] == "draftkings"


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


def test_nfl_framework_tuning_latest_endpoint_shape(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    response = client.get("/nfl/ops/framework-tuning/latest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["latest"]["payload"]["status"] == "ok"
    assert payload["latest"]["top_candidates"][0]["rank"] == 1


def test_nfl_decomposition_drift_latest_endpoint_shape(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    response = client.get("/nfl/ops/decomposition-drift/latest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["latest"]["status"] == "warning"
    assert payload["latest"]["top_shifts"][0]["factor"] == "travel_schedule"


def test_nfl_intel_routes_contracts(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)

    rosters = client.get("/nfl/intel/rosters", params={"season": 2026, "week": 7, "team": "BUF"})
    assert rosters.status_code == 200
    assert rosters.json()["count"] == 1
    assert rosters.json()["rows"][0]["depth_slot"] == "starter"
    assert rosters.json()["source_diagnostics"]["active_source"] == "nfl_com"

    stats = client.get("/nfl/intel/stats", params={"season": 2026, "week": 7})
    assert stats.status_code == 200
    assert "pass_rate" in stats.json()["rows"][0]
    assert stats.json()["rows"][0]["stats_source"] == "nfl_com"
    assert stats.json()["rows"][0]["pass_rate"] == 0.591
    assert stats.json()["rows"][0]["epa_per_play_offense"] == 0.114
    assert stats.json()["rows"][0]["epa_per_play_defense_allowed"] == -0.044
    assert stats.json()["source_diagnostics"]["active_source"] == "nfl_com"

    standings = client.get("/nfl/intel/standings", params={"season": 2026, "week": 7})
    assert standings.status_code == 200
    assert standings.json()["rows"][0]["team"] == "BUF"
    assert standings.json()["rows"][0]["win_pct"] == 0.857
    assert standings.json()["rows"][0]["conference"] == "AFC"
    assert standings.json()["rows"][0]["division"] == "East"
    assert standings.json()["rows"][1]["team"] == "NE"
    assert standings.json()["rows"][1]["win_pct"] == 0.714

    depth = client.get("/nfl/intel/depth-charts", params={"season": 2026, "week": 7, "team": "BUF"})
    assert depth.status_code == 200
    assert depth.json()["rows"][0]["position"] == "QB"
    assert depth.json()["rows"][0]["role_confidence"] == 0.923

    injuries = client.get("/nfl/intel/injuries", params={"season": 2026, "week": 7, "team": "BUF"})
    assert injuries.status_code == 200
    assert injuries.json()["rows"][0]["report_status"] == "Questionable"


def test_nfl_intel_canonicalizes_la_to_lar(monkeypatch) -> None:
    """Product Truth Layer is LAR; nflverse intel storage is LA."""

    class _LarSession(_NflRouteSession):
        def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
            sql = " ".join(str(statement).split()).lower()
            params = params or {}
            if "from nfl_dp_standings_weekly" in sql and "from standings order by" in sql:
                assert params.get("team") in (None, "LA")
                return _FakeResult(
                    [
                        {
                            "season": 2025,
                            "week": 22,
                            "team": "LA",
                            "wins": 10,
                            "losses": 7,
                            "ties": 0,
                            "points_for": 300,
                            "points_against": 280,
                            "point_diff": 20,
                            "win_pct": 0.588,
                            "conference": "NFC",
                            "division": "West",
                            "conference_wins": None,
                            "conference_losses": None,
                            "conference_ties": None,
                            "conference_pct": None,
                            "division_wins": None,
                            "division_losses": None,
                            "division_ties": None,
                            "division_pct": None,
                        }
                    ]
                )
            if "from nfl_dp_team_situational_weekly t" in sql:
                assert params.get("team") in (None, "LA")
                return _FakeResult(
                    [
                        {
                            "season": 2025,
                            "week": 22,
                            "team": "LA",
                            "games_played": 17,
                            "offensive_plays": 1000,
                            "defensive_plays": 1000,
                            "pass_rate": 0.55,
                            "early_down_pass_rate": 0.5,
                            "red_zone_td_rate": 0.6,
                            "pressure_rate_allowed": 0.2,
                            "pressure_rate_generated": 0.25,
                            "success_rate_offense": 0.45,
                            "success_rate_defense_allowed": 0.42,
                            "epa_per_play_offense": 0.112,
                            "epa_per_play_defense_allowed": -0.041,
                            "stats_source": "nflverse",
                            "wins": 10,
                            "losses": 7,
                            "ties": 0,
                            "points_for": 300,
                            "points_against": 280,
                            "point_diff": 20,
                            "win_pct": 0.588,
                            "standings_source": "nflverse",
                        }
                    ]
                )
            return super().execute(statement, params)

    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _LarSession())
    client = TestClient(app)

    standings = client.get("/nfl/intel/standings", params={"season": 2025, "week": 22, "team": "LAR"})
    assert standings.status_code == 200
    payload = standings.json()
    assert payload["team"] == "LAR"
    assert payload["selection"]["resolved"]["team"] == "LAR"
    assert payload["selection"]["resolved"]["storage_team"] == "LA"
    assert payload["rows"][0]["team"] == "LAR"

    stats = client.get("/nfl/intel/stats", params={"season": 2025, "week": 22, "team": "LAR"})
    assert stats.status_code == 200
    assert stats.json()["rows"][0]["team"] == "LAR"
    assert stats.json()["rows"][0]["epa_per_play_offense"] == 0.112


def test_intel_storage_and_serialize_helpers() -> None:
    assert nfl_routes._intel_storage_team("LAR") == "LA"
    assert nfl_routes._intel_storage_team("LA") == "LA"
    assert nfl_routes._intel_storage_team("PHI") == "PHI"
    row = _FakeRow({"team": "LA", "wins": 10, "epa_per_play_offense": 0.11234})
    serialized = nfl_routes._serialize_intel_rows([row])
    assert serialized[0]["team"] == "LAR"
    assert serialized[0]["epa_per_play_offense"] == 0.112


def test_nfl_intel_routes_default_filters(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    response = client.get("/nfl/intel/standings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["season"] == 2025
    assert payload["week"] == 22
    assert payload["selection"]["used_default"]["any"] is True
    assert payload["selection"]["latest_available"]["season"] == 2025
    assert payload["selection"]["latest_available"]["week"] == 22


def test_nfl_intel_explicit_empty_selection_preserved(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    response = client.get("/nfl/intel/standings", params={"season": 2026, "week": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["season"] == 2026
    assert payload["week"] == 1
    assert payload["count"] == 0
    assert payload["selection"]["used_default"]["any"] is False
    assert payload["selection"]["requested_availability"]["has_data"] is False
    assert payload["selection"]["latest_available"]["season"] == 2025
    assert payload["selection"]["latest_available"]["week"] == 22


def test_nfl_intel_default_resolution_consistent_across_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    endpoints = ["rosters", "stats", "standings", "depth-charts", "injuries"]

    for endpoint in endpoints:
        response = client.get(f"/nfl/intel/{endpoint}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["season"] == 2025
        assert payload["week"] == 22
        assert payload["count"] > 0
        assert payload["selection"]["used_default"]["any"] is True
        assert payload["selection"]["latest_available"]["season"] == 2025
        assert payload["selection"]["latest_available"]["week"] == 22


def test_nfl_intel_standings_returns_safe_payload_when_schema_missing(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _MissingIntelTableSession())
    client = TestClient(app)
    response = client.get("/nfl/intel/standings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["rows"] == []
    assert payload["availability"]["status"] == "unavailable"
    assert payload["availability"]["reason"] == "schema_not_ready"
    assert "nfl_dp_standings_weekly" in payload["availability"]["diagnostics"]["schema"]["missing_tables"]


def test_nfl_intel_health_schema_and_availability(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _NflRouteSession())
    client = TestClient(app)
    response = client.get("/nfl/intel/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["schema"]["stats"]["schema_ready"] is True
    assert payload["availability"]["standings"]["season"] == 2025
    assert payload["active_sources"]["rosters"] == "nfl_com"
    assert payload["active_sources"]["stats"] == "nfl_com"


def test_first_open_odds_uses_team_date_candidate_games() -> None:
    """Parallel Odds UUID must not silently blank Open (DAL@NYG class)."""

    class _Session:
        def __init__(self) -> None:
            self.sql = ""
            self.params: Dict[str, Any] = {}

        def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
            self.sql = str(statement)
            self.params = dict(params or {})
            return _FakeResult(
                [
                    {
                        "game_id": "c1df8ae6-458e-4b33-9805-94c5fd3436c7",
                        "open_spread_home": -3.0,
                        "open_total": 47.5,
                        "odds_captured_at": None,
                        "source_game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    }
                ]
            )

    session = _Session()
    out = nfl_routes._first_open_odds_by_game_ids(
        session,
        ["c1df8ae6-458e-4b33-9805-94c5fd3436c7"],
        games=[
            {
                "game_id": "c1df8ae6-458e-4b33-9805-94c5fd3436c7",
                "home_abbr": "NYG",
                "away_abbr": "DAL",
                "game_date": date(2026, 9, 13),
            }
        ],
    )
    assert "candidate_games" in session.sql
    assert session.params["home_abbrs"] == ["NYG"]
    assert session.params["away_abbrs"] == ["DAL"]
    snap = out["c1df8ae6-458e-4b33-9805-94c5fd3436c7"]
    assert snap["open_spread_home"] == -3.0
    assert snap["open_total"] == 47.5
    assert snap["open_join_status"] == "alias"


def test_first_open_odds_exact_uuid_without_game_metadata() -> None:
    class _Session:
        def __init__(self) -> None:
            self.sql = ""

        def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
            self.sql = str(statement)
            return _FakeResult([])

    session = _Session()
    nfl_routes._first_open_odds_by_game_ids(
        session, ["c1df8ae6-458e-4b33-9805-94c5fd3436c7"]
    )
    assert "candidate_games" not in session.sql
    assert "ANY(:game_ids)" in session.sql


def test_nfl_open_abbr_aliases_rams_and_washington() -> None:
    assert nfl_routes._nfl_open_abbr_aliases("LAR") == ["LA", "LAR"]
    assert nfl_routes._nfl_open_abbr_aliases("WAS") == ["WSH", "WAS"]
    assert nfl_routes._nfl_open_abbr_aliases("SEA") == ["SEA"]
