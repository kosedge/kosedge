from __future__ import annotations

import os
from datetime import datetime, timezone
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

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self._mapping.values())[key]
        return self._mapping[key]


class _Result:
    def __init__(self, rows: list[Dict[str, Any]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[_FakeRow]:
        return [_FakeRow(row) for row in self._rows]

    def fetchone(self) -> Optional[_FakeRow]:
        if not self._rows:
            return None
        return _FakeRow(self._rows[0])


class _Session:
    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _Result:
        sql = " ".join(str(statement).split()).lower()
        if "from nfl_model_runtime_state" in sql:
            return _Result([{"active_model_version": "nfl-v1.5-matchup-sim"}])
        if "from nfl_dp_schedules" in sql and "spread_home" not in sql:
            return _Result([{"week": 1}])
        if "odds_snapshots" in sql:
            return _Result([])
        if "from nfl_market_projections np" in sql and "spread_home" in sql:
            return _Result(
                [
                    {
                        "game_id": "g-sea-ne",
                        "start_time": datetime.now(timezone.utc),
                        "game_date": datetime.now(timezone.utc).date(),
                        "season": 2026,
                        "home_team": "SEA",
                        "home_abbr": "SEA",
                        "away_team": "NE",
                        "away_abbr": "NE",
                        "home_win_prob": 0.6189,
                        "away_win_prob": 0.3811,
                        "spread_home": -3.47,
                        "total_mean": 41.29,
                        "fair_home_ml": -162,
                        "fair_away_ml": 162,
                        "model_version": "nfl-v1.5-matchup-sim",
                        "simulation_count": 4000,
                        "projection_created_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_player_projection_baselines" in sql:
            return _Result(
                [
                    {
                        "season": 2026,
                        "week": 1,
                        "team": "BUF",
                        "player_id": "p1",
                        "player_uid": "uid-p1",
                        "player_name": "Player A",
                        "position": "WR",
                        "model_version": "nfl-player-v1",
                        "pass_yards_mean": 0.0,
                        "rush_yards_mean": 6.0,
                        "receiving_yards_mean": 84.0,
                        "receptions_mean": 6.3,
                        "anytime_td_prob": 0.42,
                        "floor_outcome": {},
                        "median_outcome": {},
                        "ceiling_outcome": {},
                        "uncertainty": {},
                        "source_coverage": {},
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_player_prop_model_edges" in sql:
            return _Result(
                [
                    {
                        "season": 2026,
                        "week": 1,
                        "model_version": "nfl-player-v1",
                        "player_name": "Player A",
                        "player_uid": "uid-p1",
                        "team": "BUF",
                        "market_key": "rec_yds",
                        "line": 72.5,
                        "edge_over": 0.06,
                        "edge_under": -0.06,
                        "confidence": 0.81,
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_fantasy_weekly_projections" in sql:
            return _Result(
                [
                    {
                        "season": 2026,
                        "week": 1,
                        "scoring_profile": "half_ppr",
                        "model_version": "nfl-player-v1",
                        "player_id": "p1",
                        "player_uid": "uid-p1",
                        "player_name": "Player A",
                        "team": "BUF",
                        "position": "WR",
                        "expected_points": 17.2,
                        "floor_points": 10.1,
                        "median_points": 16.8,
                        "ceiling_points": 24.3,
                        "rank_overall": 7,
                        "rank_position": 4,
                        "tier": 1,
                        "projection_payload": {},
                        "updated_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "from nfl_projection_audit_runs" in sql:
            return _Result(
                [
                    {
                        "layer": "player_baseline",
                        "readiness_status": "go",
                        "source_coverage": {},
                        "freshness": {},
                        "calibration_flags": {},
                        "metrics": {},
                        "created_at": datetime.now(timezone.utc),
                    },
                    {
                        "layer": "props",
                        "readiness_status": "go",
                        "source_coverage": {},
                        "freshness": {},
                        "calibration_flags": {},
                        "metrics": {},
                        "created_at": datetime.now(timezone.utc),
                    },
                ]
            )
        raise AssertionError(f"Unexpected SQL: {sql}")

    def close(self) -> None:
        return None


def test_projection_endpoints_contract(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Session())
    client = TestClient(app)

    players = client.get("/nfl/projections/players", params={"season": 2026, "week": 1})
    assert players.status_code == 200
    assert players.json()["count"] == 1

    props = client.get("/nfl/props/board", params={"season": 2026, "week": 1})
    assert props.status_code == 200
    assert props.json()["rows"][0]["market_key"] == "rec_yds"
    assert props.json()["diagnostics"]["kosedge_only"] is True

    fantasy = client.get(
        "/nfl/fantasy/rankings",
        params={"season": 2026, "week": 1, "scoring_profile": "half_ppr"},
    )
    assert fantasy.status_code == 200
    assert fantasy.json()["rows"][0]["rank_overall"] == 7

    readiness = client.get("/nfl/ops/projections-readiness", params={"season": 2026, "week": 1})
    assert readiness.status_code == 200
    assert readiness.json()["overall_status"] == "go"


def test_nfl_fair_lines_returns_kosedge_board_when_odds_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Session())

    def _boom(**_kwargs):
        raise RuntimeError("odds feed down")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    client = TestClient(app)
    response = client.get("/nfl/fair-lines", params={"season": 2026, "days_ahead": 120})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["diagnostics"]["kosedge_only"] is True
    assert payload["diagnostics"]["odds_feed_status"] == "degraded"
    line = payload["lines"][0]
    assert line["home_abbr"] == "SEA"
    assert line["away_abbr"] == "NE"
    assert line["spread_home"] == -3.47
    assert line["total_mean"] == 41.29
    assert line["fair_home_ml"] == -162
    assert line["market_home_ml"] is None
    assert line["market_spread_home"] is None
    assert payload["diagnostics"].get("snapshot_current_count", 0) == 0


def test_nfl_fair_lines_uses_snapshot_current_when_odds_401(monkeypatch) -> None:
    """Live Odds 401 → Current from latest odds_snapshots, Open stays first capture."""

    class _SnapshotSession(_Session):
        def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _Result:
            sql = " ".join(str(statement).split()).lower()
            if "odds_snapshots" in sql:
                return _Result(
                    [
                        {
                            "game_id": "g-sea-ne",
                            "open_spread_home": -3.0,
                            "open_total": 44.0,
                            "current_spread_home": -3.5,
                            "current_total": 44.5,
                            "odds_captured_at": datetime(2026, 8, 21, 13, 42, 55, tzinfo=timezone.utc),
                            "source_game_id": "g-sea-ne",
                        }
                    ]
                )
            return super().execute(statement, params)

    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _SnapshotSession())

    def _boom(**_kwargs):
        raise RuntimeError(
            "401 Client Error: Unauthorized for url: "
            "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
            "?apiKey=3cf941bb533372b5533a0c9b946e7400"
        )

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    client = TestClient(app)
    response = client.get("/nfl/fair-lines", params={"season": 2026, "days_ahead": 120})
    assert response.status_code == 200
    payload = response.json()
    diag = payload["diagnostics"]
    assert diag["odds_feed_status"] == "degraded"
    assert "3cf941bb" not in str(diag.get("odds_feed_error") or "")
    assert diag["snapshot_current_count"] == 1
    assert diag["market_joined_count"] == 1
    assert diag["kosedge_only"] is False
    assert diag["current_source"] == "odds_snapshots"
    line = payload["lines"][0]
    assert line["away_abbr"] == "NE"
    assert line["home_abbr"] == "SEA"
    assert line["open_spread_home"] == -3.0
    assert line["open_total"] == 44.0
    assert line["market_spread_home"] == -3.5
    assert line["market_total"] == 44.5
    assert line["market_spread_home"] != line["open_spread_home"]
    assert line["market_source"] == "odds_snapshots"
    decision = line.get("decision") or {}
    spread = decision.get("spread") or {}
    assert (spread.get("market_line") or spread.get("marketLine")) == -3.5
    hygiene = diag.get("current_hygiene") or {}
    assert hygiene.get("kept_spread") == 1
    assert hygiene.get("rejected_spread") == 0


def test_nfl_fair_lines_rejects_snapshot_avg_garbage(monkeypatch) -> None:
    """AVG tenths (3.8 / −3.58 class) must not paint Current; Open stays."""

    class _SnapshotSession(_Session):
        def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _Result:
            sql = " ".join(str(statement).split()).lower()
            if "odds_snapshots" in sql:
                return _Result(
                    [
                        {
                            "game_id": "g-sea-ne",
                            "open_spread_home": -3.5,
                            "open_total": 44.5,
                            "current_spread_home": -3.58,
                            "current_total": 44.42,
                            "odds_captured_at": datetime(2026, 8, 21, 13, 42, 55, tzinfo=timezone.utc),
                            "source_game_id": "g-sea-ne",
                        }
                    ]
                )
            return super().execute(statement, params)

    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _SnapshotSession())

    def _boom(**_kwargs):
        raise RuntimeError("401 Client Error: Unauthorized")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    client = TestClient(app)
    response = client.get("/nfl/fair-lines", params={"season": 2026, "days_ahead": 120})
    assert response.status_code == 200
    payload = response.json()
    diag = payload["diagnostics"]
    line = payload["lines"][0]
    assert line["open_spread_home"] == -3.5
    assert line["open_total"] == 44.5
    assert line["market_spread_home"] is None
    assert line["market_total"] is None
    assert line["best_spread_home"] is None
    assert line["best_total"] is None
    assert diag.get("snapshot_current_count") == 0
    hygiene = diag.get("current_hygiene") or {}
    assert hygiene.get("snapshot_spread_rejected") == 1
    assert hygiene.get("snapshot_total_rejected") == 1
    decision = line.get("decision") or {}
    spread = decision.get("spread") or {}
    assert spread.get("market_line") is None
    assert spread.get("reason") == "missing_fair_or_market"
