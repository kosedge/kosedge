from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.main import app
from src.routes import mlb as mlb_routes


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
        if not self._rows:
            return None
        return _FakeRow(self._rows[0])

    def fetchall(self) -> List[_FakeRow]:
        return [_FakeRow(row) for row in self._rows]

    def scalar_one(self) -> Any:
        return self._scalar


class _StatefulRouteSession:
    def __init__(self, state: Dict[str, Any]) -> None:
        self.state = state
        self.committed = False
        self.rolled_back = False

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        params = params or {}

        if "select state_key, active_model_version, previous_model_version, reason, updated_at" in sql:
            active_model = self.state.get("active_model")
            if active_model is None:
                return _FakeResult([])
            return _FakeResult([active_model])

        if "select active_model_version from mlb_model_runtime_state" in sql:
            active_model = self.state.get("active_model")
            if active_model is None:
                return _FakeResult([])
            return _FakeResult([
                {"active_model_version": active_model["active_model_version"]}
            ])

        if "insert into mlb_model_runtime_state" in sql:
            previous = self.state.get("active_model", {}).get("active_model_version")
            self.state["active_model"] = {
                "state_key": params["state_key"],
                "active_model_version": params["active_model_version"],
                "previous_model_version": previous,
                "reason": params["reason"],
                "updated_at": datetime.now(timezone.utc),
            }
            return _FakeResult([])

        if "select run_date, payload, created_at from mlb_model_run_snapshots" in sql:
            snapshot = self.state.get("quality_snapshot")
            if snapshot is None:
                return _FakeResult([])
            return _FakeResult([snapshot])

        if "select count(*)::int as c from mlb_alert_events" in sql or "select count(*)::int from mlb_alert_events" in sql:
            return _FakeResult(scalar=int(self.state.get("warning_alerts", 0)))

        raise AssertionError(f"Unexpected SQL in route test: {sql}")

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        return None


def test_active_model_routes_round_trip(monkeypatch) -> None:
    state: Dict[str, Any] = {}
    monkeypatch.setattr(mlb_routes, "SessionLocal", lambda: _StatefulRouteSession(state))

    client = TestClient(app)

    get_default = client.get("/mlb/ops/active-model")
    assert get_default.status_code == 200
    assert get_default.json()["active_model_version"] == "mlb-v1-pa-sim"
    assert get_default.json()["reason"] == "default"

    post_resp = client.post(
        "/mlb/ops/active-model",
        params={"model_version": "mlb-v2-pitch-sim", "reason": "holdout-win"},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["active_model_version"] == "mlb-v2-pitch-sim"
    assert post_resp.json()["previous_model_version"] is None

    get_after = client.get("/mlb/ops/active-model")
    assert get_after.status_code == 200
    assert get_after.json()["active_model_version"] == "mlb-v2-pitch-sim"
    assert get_after.json()["reason"] == "holdout-win"


def test_go_no_go_route_uses_quality_snapshot_and_alerts(monkeypatch) -> None:
    state = {
        "quality_snapshot": {
            "run_date": date.today().isoformat(),
            "payload": {
                "sample_size": 164,
                "calendar_days_covered": 18,
                "last_game_date": date.today().isoformat(),
                "brier_ml": 0.2461,
                "mae_total_runs": 1.29,
                "avg_ml_clv": 0.0061,
                "avg_total_clv": 0.0114,
            },
            "created_at": datetime.now(timezone.utc),
        },
        "warning_alerts": 0,
    }
    monkeypatch.setattr(mlb_routes, "SessionLocal", lambda: _StatefulRouteSession(state))

    client = TestClient(app)
    response = client.get(
        "/mlb/ops/go-no-go",
        params={"model_version": "mlb-v2-pitch-sim"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "green"
    assert payload["checks"]["sample_size_ok"] is True
    assert payload["checks"]["calendar_days_ok"] is True
    assert payload["checks"]["freshness_ok"] is True
    assert payload["recent_warning_alerts_24h"] == 0
    assert payload["metrics"]["brier_ml"] == 0.2461


def test_simulation_route_passes_offense_context_into_inputs(monkeypatch) -> None:
    captured: Dict[str, Any] = {}

    class _SimulationSession:
        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    def _fake_fetch_game_row(session: Any, game_id: str) -> Dict[str, Any]:
        assert game_id == "game-123"
        return {
            "game_id": game_id,
            "home_team": "Los Angeles Dodgers",
            "away_team": "Atlanta Braves",
            "probable_pitcher_home": "Tyler Glasnow",
            "probable_pitcher_away": "Chris Sale",
            "weather_temp_f": 77.0,
            "weather_wind_mph": 9.0,
            "weather_wind_dir_deg": 190.0,
            "weather_humidity_pct": 51.0,
            "park_factor_runs": 1.01,
            "lineup_confidence_home": 0.96,
            "lineup_confidence_away": 0.94,
            "offense_index_home": 1.08,
            "offense_index_away": 1.03,
            "offense_split_index_home": 1.12,
            "offense_split_index_away": 0.97,
            "recent_form_index_home": 1.09,
            "recent_form_index_away": 0.98,
            "lineup_strength_index_home": 1.11,
            "lineup_strength_index_away": 0.96,
            "bullpen_fatigue_home": 0.54,
            "bullpen_fatigue_away": 0.49,
            "bullpen_ip_last3_home": 8.2,
            "bullpen_ip_last3_away": 10.6,
            "bullpen_availability_home": 0.71,
            "bullpen_availability_away": 0.63,
            "bullpen_high_leverage_availability_home": 0.69,
            "bullpen_high_leverage_availability_away": 0.58,
            "context_updated_at": datetime.now(timezone.utc),
            "umpire_run_factor": 1.02,
            "umpire_home_plate": "Mark Wegner",
            "lineup_confirmed": True,
        }

    def _fake_starter_identity_features(name: Optional[str]) -> Dict[str, Any]:
        return {
            "starter_quality": 0.94 if name == "Chris Sale" else 0.97,
            "k_factor": 1.14 if name == "Chris Sale" else 1.09,
            "bb_factor": 0.93,
            "gb_factor": 1.02,
        }

    def _fake_run_simulation_by_model(inputs: Any, *, simulations: int, model_version: str) -> Dict[str, Any]:
        captured["inputs"] = inputs
        captured["simulations"] = simulations
        captured["model_version"] = model_version
        return {
            "game_id": inputs.game_id,
            "model_version": model_version,
            "simulation_count": simulations,
            "inputs": {"home_team": inputs.home_team, "away_team": inputs.away_team},
            "run_rates": {"offense_home_f5": 1.0},
            "markets": {
                "f5_home_win_prob": 0.53,
                "fg_home_win_prob": 0.56,
                "f5_total_mean": 4.6,
                "fg_total_mean": 8.8,
                "fair_f5_home_ml": -113,
                "fair_fg_home_ml": -127,
                "fair_f5_total": 4.5,
                "fair_fg_total": 9.0,
            },
            "diagnostics": {},
        }

    monkeypatch.setattr(mlb_routes, "SessionLocal", lambda: _SimulationSession())
    monkeypatch.setattr(mlb_routes, "_fetch_game_row", _fake_fetch_game_row)
    monkeypatch.setattr(mlb_routes, "starter_identity_features", _fake_starter_identity_features)
    monkeypatch.setattr(mlb_routes, "_run_simulation_by_model", _fake_run_simulation_by_model)
    monkeypatch.setattr(mlb_routes, "_store_projection", lambda session, projection: None)

    client = TestClient(app)
    response = client.post(
        "/mlb/simulations/game-123",
        params={"simulations": 1200, "model_version": "mlb-v2-pitch-sim"},
    )

    assert response.status_code == 200
    assert response.json()["markets"]["fg_home_win_prob"] == 0.56
    assert captured["simulations"] == 1200
    assert captured["model_version"] == "mlb-v2-pitch-sim"
    assert captured["inputs"].offense_home == 1.08
    assert captured["inputs"].offense_split_home == 1.12
    assert captured["inputs"].recent_form_index_home == 1.09
    assert captured["inputs"].lineup_strength_index_home == 1.11
    assert captured["inputs"].offense_split_away == 0.97
    assert captured["inputs"].lineup_confirmed is True


def test_premium_feed_applies_uncertainty_guardrails(monkeypatch) -> None:
    def _fake_edges_today(model_version: Optional[str] = None) -> Dict[str, Any]:
        return {
            "model_version": model_version or "mlb-v1-pa-sim",
            "count": 2,
            "edges": [
                {
                    "game_id": "g-safe",
                    "home_team": "Los Angeles Dodgers",
                    "away_team": "San Diego Padres",
                    "quality_score": 82.0,
                    "freshness_score": 0.86,
                    "market_depth": 14,
                    "ml_edge_prob": 0.021,
                    "total_edge": 0.8,
                    "recommended_stake_fraction": 0.012,
                    "uncertainty_score": 0.33,
                    "ml_confidence_interval_width": 0.11,
                    "total_band_width": 3.8,
                    "explainability": {"drivers": []},
                },
                {
                    "game_id": "g-risky",
                    "home_team": "Boston Red Sox",
                    "away_team": "New York Yankees",
                    "quality_score": 88.0,
                    "freshness_score": 0.91,
                    "market_depth": 16,
                    "ml_edge_prob": 0.028,
                    "total_edge": 1.1,
                    "recommended_stake_fraction": 0.014,
                    "uncertainty_score": 0.88,
                    "ml_confidence_interval_width": 0.22,
                    "total_band_width": 7.1,
                    "explainability": {"drivers": []},
                },
            ],
        }

    monkeypatch.setattr(mlb_routes, "mlb_edges_today", _fake_edges_today)
    client = TestClient(app)
    response = client.get("/mlb/edges/premium-feed")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert all(x["game_id"] == "g-safe" for x in payload["recommendations"])
    assert payload["portfolio_summary"]["rejected_counts"]["uncertainty"] >= 1
