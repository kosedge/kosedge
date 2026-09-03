"""Nullable prop confidence — storage + read-path regression (PR 428 follow-up).

PR 428 returns honest NULL confidence for projection-only rows, one-way ATD,
and other unscorable cases. The DB column must accept NULL; board ordering and
filters must not treat NULL as 0 or sort it ahead of scored rows.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.main import app
from src.routes import nfl as nfl_routes
from src.services.nfl_prop_edge_policy import anytime_td_prob_from_td_mean
from src.services.nfl_props_eligibility import is_investable_prop


class _Result:
    def __init__(self, rows=None, row=None, rowcount=0):
        self._rows = rows or []
        self._row = row
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class _FakeRow:
    def __init__(self, mapping: Dict[str, Any]) -> None:
        self._mapping = mapping

    def __getattr__(self, name: str) -> Any:
        return self._mapping[name]


def _qb_baseline(
    *,
    player_id: str,
    player_name: str,
    team: str,
    pass_yards_mean: float = 245.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        season=2026,
        week=1,
        team=team,
        player_id=player_id,
        player_uid=f"uid-{player_id}",
        player_name=player_name,
        position="QB",
        game_id=None,
        pass_yards_mean=pass_yards_mean,
        pass_yards_std=35.0,
        rush_yards_mean=12.0,
        rush_yards_std=8.0,
        receiving_yards_mean=0.0,
        receiving_yards_std=1.0,
        receptions_mean=0.0,
        receptions_std=0.5,
        pass_tds_mean=1.8,
        rush_tds_mean=0.08,
        rec_tds_mean=0.0,
        total_tds_mean=1.88,
        anytime_td_prob=anytime_td_prob_from_td_mean(0.08),
    )


def _wr_baseline(
    *,
    player_id: str,
    player_name: str,
    team: str,
    receiving_yards_mean: float = 72.0,
    anytime_td_prob: float = 0.41,
) -> SimpleNamespace:
    return SimpleNamespace(
        season=2026,
        week=1,
        team=team,
        player_id=player_id,
        player_uid=f"uid-{player_id}",
        player_name=player_name,
        position="WR",
        game_id=None,
        pass_yards_mean=0.0,
        pass_yards_std=3.0,
        rush_yards_mean=2.0,
        rush_yards_std=3.0,
        receiving_yards_mean=receiving_yards_mean,
        receiving_yards_std=18.0,
        receptions_mean=5.5,
        receptions_std=2.0,
        pass_tds_mean=0.0,
        rush_tds_mean=0.0,
        rec_tds_mean=0.35,
        total_tds_mean=0.35,
        anytime_td_prob=anytime_td_prob,
    )


def _feature(player_id: str, team: str, position: str, role_confidence: float = 0.85) -> SimpleNamespace:
    return SimpleNamespace(
        player_id=player_id,
        team=team,
        position=position,
        role_confidence=role_confidence,
        availability_confidence=0.9,
        target_proxy=0.22,
        rush_share=0.02,
    )


class _NullableConfidenceMaterializerSession:
    """Exercises full materialize_nfl_player_props_edges write path."""

    def __init__(
        self,
        *,
        baselines: list,
        features: list,
        market_rows: Optional[list] = None,
    ):
        self.baselines = baselines
        self.features = features
        self.market_rows = market_rows or []
        self.inserts: list[dict] = []
        self.committed = False

    def execute(self, sql, params=None):
        query = str(sql)
        params = dict(params or {})
        if "SELECT COALESCE(MAX(week), 1)::int AS week" in query:
            return _Result(row=(1,))
        if "FROM nfl_player_projection_features_weekly" in query and "role_confidence" in query:
            return _Result(rows=self.features)
        if "FROM nfl_dp_depth_chart_weekly" in query:
            return _Result(rows=[])
        if "FROM nfl_player_game_box_score_sims" in query:
            return _Result(rows=[])
        if "FROM nfl_player_projection_baselines" in query and "model_version" in query:
            return _Result(rows=self.baselines)
        if "FROM nfl_player_prop_market_snapshots" in query and "SELECT DISTINCT ON" in query:
            return _Result(rows=self.market_rows)
        if "DELETE FROM nfl_player_prop_model_edges" in query:
            return _Result(rowcount=0)
        if "INSERT INTO nfl_player_prop_model_edges" in query:
            self.inserts.append(params)
            return _Result()
        if "INSERT INTO nfl_projection_audit_runs" in query:
            return _Result()
        raise AssertionError(f"Unexpected SQL in nullable confidence materializer test: {query}")

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        return None


def test_materializer_persists_null_confidence_for_projection_only_and_one_way_atd(
    monkeypatch,
) -> None:
    """Regression: NOT NULL violation on projection-only pass_yds and one-way ATD."""
    qb = _qb_baseline(
        player_id="p-brissett",
        player_name="J.Brissett",
        team="ARI",
        pass_yards_mean=238.0,
    )
    wr = _wr_baseline(
        player_id="p-sutton",
        player_name="C.Sutton",
        team="DEN",
        anytime_td_prob=0.4055,
    )
    one_way_atd_market = SimpleNamespace(
        id="snap-atd",
        season=2026,
        week=1,
        game_id=None,
        player_id="p-sutton",
        player_uid="uid-p-sutton",
        player_name="C.Sutton",
        team="DEN",
        sportsbook="draftkings",
        market_key="anytime_td",
        line=0.5,
        over_price=-150,
        under_price=None,
        captured_at=None,
    )

    session = _NullableConfidenceMaterializerSession(
        baselines=[qb, wr],
        features=[
            _feature("p-brissett", "ARI", "QB"),
            _feature("p-sutton", "DEN", "WR"),
        ],
        market_rows=[one_way_atd_market],
    )
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)

    payload = tasks.materialize_nfl_player_props_edges(
        season=2026, week=1, model_version="nfl-player-v1"
    )

    assert session.committed is True
    assert payload["prop_edges_upserted"] >= 2

    pass_yds = [r for r in session.inserts if r.get("market_key") == "pass_yds" and r.get("player_name") == "J.Brissett"]
    assert len(pass_yds) == 1
    assert pass_yds[0]["line"] is None
    assert pass_yds[0]["confidence"] is None
    assert pass_yds[0]["confidence"] != 0

    atd = [r for r in session.inserts if r.get("market_key") == "anytime_td" and r.get("player_name") == "C.Sutton"]
    assert len(atd) == 1
    assert atd[0]["confidence"] is None
    assert atd[0]["market_over_price"] == -150
    assert atd[0]["market_under_price"] is None


class _PropsBoardSession:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self.rows = rows
        self.last_board_sql: Optional[str] = None

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None) -> _Result:
        sql = " ".join(str(statement).split())
        sql_lower = sql.lower()
        if "from nfl_player_prop_model_edges" in sql_lower:
            self.last_board_sql = sql
            min_conf = float((params or {}).get("min_confidence", 0.0))
            kept = []
            for row in self.rows:
                conf = row.get("confidence")
                if min_conf > 0 and conf is not None and conf < min_conf:
                    continue
                kept.append(row)

            def _sort_key(r: Dict[str, Any]) -> tuple:
                tag = (r.get("diagnostics") or {}).get("tag", "PASS")
                tag_rank = {"PLAY": 0, "WATCH": 1, "LEAN": 1}.get(tag, 2)
                conf = r.get("confidence")
                conf_sort = conf if conf is not None else float("-inf")
                edge = max(
                    abs(float(r.get("edge_over") or 0)),
                    abs(float(r.get("edge_under") or 0)),
                )
                return (tag_rank, conf_sort, edge)

            kept.sort(key=_sort_key, reverse=True)
            return _Result(rows=[_FakeRow(row) for row in kept])
        raise AssertionError(f"Unexpected SQL in props board test: {sql}")

    def close(self) -> None:
        return None


def _board_row(
    *,
    player_name: str,
    market_key: str = "rec_yds",
    confidence: Optional[float],
    edge_over: Optional[float] = 0.06,
    edge_under: Optional[float] = -0.06,
    market_over_price: Optional[int] = None,
    market_under_price: Optional[int] = None,
    line: Optional[float] = 72.5,
    model_mean: float = 80.0,
    position: str = "WR",
) -> Dict[str, Any]:
    return {
        "season": 2026,
        "week": 1,
        "model_version": "nfl-player-v1",
        "game_id": None,
        "player_id": f"p-{player_name.lower()}",
        "player_uid": f"uid-{player_name.lower()}",
        "player_name": player_name,
        "team": "BUF",
        "market_key": market_key,
        "line": line,
        "model_mean": model_mean,
        "model_std": 18.0,
        "model_floor": 50.0,
        "model_median": 78.0,
        "model_ceiling": 105.0,
        "over_prob": 0.58,
        "under_prob": 0.42,
        "fair_over_price": -120,
        "fair_under_price": 110,
        "market_over_price": market_over_price,
        "market_under_price": market_under_price,
        "edge_over": edge_over,
        "edge_under": edge_under,
        "confidence": confidence,
        "diagnostics": {
            "tag": "WATCH",
            "position": position,
            "role_confidence": 0.88,
        },
        "updated_at": datetime.now(timezone.utc),
    }


def test_props_board_sql_orders_confidence_nulls_last(monkeypatch) -> None:
    board_session = _PropsBoardSession(
        [
            _board_row(player_name="HighConf", confidence=0.72),
            _board_row(
                player_name="NullConf",
                confidence=None,
                line=None,
                edge_over=None,
                edge_under=None,
            ),
        ]
    )
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: board_session)
    client = TestClient(app)
    response = client.get("/nfl/props/board", params={"season": 2026, "week": 1})
    assert response.status_code == 200
    assert board_session.last_board_sql is not None
    assert "NULLS LAST" in board_session.last_board_sql


def test_props_board_returns_null_confidence_for_one_way_anytime_td(monkeypatch) -> None:
    monkeypatch.setattr(
        nfl_routes,
        "SessionLocal",
        lambda: _PropsBoardSession(
            [
                _board_row(
                    player_name="C.Sutton",
                    market_key="anytime_td",
                    confidence=None,
                    line=0.5,
                    model_mean=0.4055,
                    edge_over=0.1265,
                    edge_under=None,
                    market_over_price=-150,
                    market_under_price=None,
                )
            ]
        ),
    )
    client = TestClient(app)
    response = client.get("/nfl/props/board", params={"season": 2026, "week": 1})
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["confidence"] is None


def test_props_board_projection_only_reads_back_null_confidence(monkeypatch) -> None:
    monkeypatch.setattr(
        nfl_routes,
        "SessionLocal",
        lambda: _PropsBoardSession(
            [
                _board_row(
                    player_name="J.Brissett",
                    market_key="pass_yds",
                    confidence=None,
                    line=None,
                    model_mean=238.0,
                    edge_over=None,
                    edge_under=None,
                    market_over_price=None,
                    market_under_price=None,
                    position="QB",
                )
            ]
        ),
    )
    client = TestClient(app)
    response = client.get("/nfl/props/board", params={"season": 2026, "week": 1})
    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["confidence"] is None
    assert row["confidence"] != 0


def test_props_board_null_confidence_sorted_after_scored_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        nfl_routes,
        "SessionLocal",
        lambda: _PropsBoardSession(
            [
                _board_row(player_name="NullConf", confidence=None, line=None, edge_over=None, edge_under=None),
                _board_row(player_name="MidConf", confidence=0.55),
                _board_row(player_name="HighConf", confidence=0.81),
            ]
        ),
    )
    client = TestClient(app)
    response = client.get("/nfl/props/board", params={"season": 2026, "week": 1})
    assert response.status_code == 200
    names = [r["player_name"] for r in response.json()["rows"]]
    assert names.index("HighConf") < names.index("MidConf")
    assert names.index("MidConf") < names.index("NullConf")


def test_props_board_min_confidence_keeps_null_confidence_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        nfl_routes,
        "SessionLocal",
        lambda: _PropsBoardSession(
            [
                _board_row(player_name="NullConf", confidence=None, line=None, edge_over=None, edge_under=None),
                _board_row(player_name="LowConf", confidence=0.20),
                _board_row(player_name="HighConf", confidence=0.70),
            ]
        ),
    )
    client = TestClient(app)
    response = client.get(
        "/nfl/props/board",
        params={"season": 2026, "week": 1, "min_confidence": 0.5},
    )
    assert response.status_code == 200
    names = {r["player_name"] for r in response.json()["rows"]}
    assert "NullConf" in names
    assert "HighConf" in names
    assert "LowConf" not in names


def test_placeholder_confidence_gate_does_not_drop_null_confidence() -> None:
    """NULL is unscorable, not a placeholder — must not trigger PLACEHOLDER_CONFIDENCE_MAX drop."""
    assert is_investable_prop(
        market_key="pass_yds",
        position="QB",
        model_mean=238.0,
        line=None,
        confidence=None,
        role_confidence=0.85,
        market_joined=False,
    )
    # Contrast: explicit low placeholder confidence still drops at the involvement floor.
    assert not is_investable_prop(
        market_key="pass_yds",
        position="QB",
        model_mean=75.0,
        line=None,
        confidence=0.08,
        role_confidence=0.85,
        market_joined=False,
    )
