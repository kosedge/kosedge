"""V1 handicap-overlay cert — Week 1 KEI cannot feed published fair/edge.

These proofs fail if ``apply_week1_kei_reprice`` is rewired into
fair-lines / survivor handicap columns that drive published fair/edge.
Coming soon / env flags are not an unlock.
"""

from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path
from typing import Any, Dict, Optional

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi.testclient import TestClient

from src.main import app
from src.routes import nfl as nfl_routes
from src.services.nfl_kei_week1_reprice import (
    PUBLISHED_FAIR_EDGE_HANDICAP_KEYS,
    WEEK1_KEI_PUBLISH_FAIL_CLOSED_REASON,
    WEEK1_KEI_PUBLISH_MUTATE_FAIR,
    Week1Pack,
    apply_week1_kei_reprice,
    apply_week1_kei_reprice_for_published_fair,
)
from tests.test_nfl_projection_endpoints import _Session


_ROUTES_PY = Path(__file__).resolve().parents[1] / "src" / "routes" / "nfl.py"
_REPRICE_PY = (
    Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_kei_week1_reprice.py"
)


def _call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_publish_mutate_fair_lock_is_hard_false() -> None:
    assert WEEK1_KEI_PUBLISH_MUTATE_FAIR is False
    assert WEEK1_KEI_PUBLISH_FAIL_CLOSED_REASON == "v1_handicap_overlay_fail_closed"
    source = inspect.getsource(apply_week1_kei_reprice_for_published_fair)
    assert "os.getenv" not in source
    assert "os.environ" not in source
    assert "coming_soon" not in source.lower() or "coming_soon_independent" in source
    assert "NFL_EDGE_BOARD_PUBLIC_ENABLED" not in source
    assert "apply_week1_kei_reprice(" not in source


def test_routes_do_not_call_live_week1_kei_reprice() -> None:
    tree = ast.parse(_ROUTES_PY.read_text(encoding="utf-8"))
    names = _call_names(tree)
    assert "apply_week1_kei_reprice" not in names
    assert "apply_week1_kei_reprice_for_published_fair" in names
    assert not hasattr(nfl_routes, "apply_week1_kei_reprice")
    assert hasattr(nfl_routes, "apply_week1_kei_reprice_for_published_fair")


def test_published_helper_never_calls_live_reprice() -> None:
    tree = ast.parse(_REPRICE_PY.read_text(encoding="utf-8"))
    helper = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == (
            "apply_week1_kei_reprice_for_published_fair"
        ):
            helper = node
            break
    assert helper is not None
    assert "apply_week1_kei_reprice" not in _call_names(helper)


def test_published_helper_is_identity_when_library_would_move_line() -> None:
    """Library still moves NE@SEA; publish binder must not."""
    stamped = {
        "spread_home": -3.0,
        "total_mean": 44.0,
        "home_win_prob": 0.58,
        "away_win_prob": 0.42,
        "fair_home_ml": -140,
        "fair_away_ml": 120,
    }
    live_h, live_log = apply_week1_kei_reprice(
        handicap=dict(stamped),
        home_abbr="SEA",
        away_abbr="NE",
        week=1,
        season=2026,
        season_type="REG",
        pack=Week1Pack.empty(),
    )
    assert live_log.get("applied") is True
    assert live_h["spread_home"] != stamped["spread_home"]

    pub_h, pub_log = apply_week1_kei_reprice_for_published_fair(
        handicap=dict(stamped),
        home_abbr="SEA",
        away_abbr="NE",
        week=1,
        season=2026,
        season_type="REG",
        pack=Week1Pack.empty(),
    )
    for key in PUBLISHED_FAIR_EDGE_HANDICAP_KEYS:
        assert pub_h[key] == stamped[key]
    assert pub_log["applied"] is False
    assert pub_log["skipped"] is True
    assert pub_log["fail_closed"] is True
    assert pub_log["reason"] == WEEK1_KEI_PUBLISH_FAIL_CLOSED_REASON
    assert pub_log["spread_delta"] == 0.0
    assert pub_log["total_delta"] == 0.0


def test_published_helper_does_not_invoke_poisoned_live_reprice(monkeypatch) -> None:
    def _poison(**_kwargs: Any) -> tuple[dict, dict]:
        raise AssertionError("apply_week1_kei_reprice reached publish helper")

    monkeypatch.setattr(
        "src.services.nfl_kei_week1_reprice.apply_week1_kei_reprice",
        _poison,
    )
    stamped = {"spread_home": -3.47, "total_mean": 41.29, "home_win_prob": 0.6189}
    out, log = apply_week1_kei_reprice_for_published_fair(
        handicap=stamped,
        week=1,
        season=2026,
        home_abbr="SEA",
        away_abbr="NE",
    )
    assert out == stamped
    assert log["applied"] is False


class _Week1FairSession(_Session):
    """Same NE@SEA fixture as projection tests, but week=1 REG 2026 (live scope)."""

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None):
        result = super().execute(statement, params)
        sql = " ".join(str(statement).split()).lower()
        if "from nfl_market_projections np" in sql and "spread_home" in sql:
            row = dict(result._rows[0])
            row["week"] = 1
            row["season"] = 2026
            result._rows = [row]
        return result


def test_fair_lines_week1_published_columns_ignore_kei_mix(monkeypatch) -> None:
    """NE@SEA Week 1 travel would move −1.0 if the live mix were reachable."""

    def _poison(**_kwargs: Any) -> tuple[dict, dict]:
        raise AssertionError("apply_week1_kei_reprice reached fair-lines publish path")

    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Week1FairSession())
    monkeypatch.setattr(
        "src.services.nfl_kei_week1_reprice.apply_week1_kei_reprice",
        _poison,
    )
    if hasattr(nfl_routes, "apply_week1_kei_reprice"):
        monkeypatch.setattr(nfl_routes, "apply_week1_kei_reprice", _poison)

    def _boom(**_kwargs: Any) -> list:
        raise RuntimeError("odds feed down")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    client = TestClient(app)
    response = client.get("/nfl/fair-lines", params={"season": 2026, "days_ahead": 120})
    assert response.status_code == 200
    payload = response.json()
    line = payload["lines"][0]
    # Stamped fixture values — live KEI travel would have painted -4.47 / 40.79.
    assert line["spread_home"] == -3.47
    assert line["handicap_spread_home"] == -3.47
    assert line["total_mean"] == 41.29
    assert line["handicap_total_mean"] == 41.29
    assert line["home_win_prob"] == 0.6189
    assert line["handicap_home_win_prob"] == 0.6189
    assert line["spread_edge"] is None
    assert line["total_edge"] is None
    assert line["ml_edge_prob"] is None
    kei = line.get("kei_reprice") or {}
    assert kei.get("applied") is False
    assert kei.get("reason") == WEEK1_KEI_PUBLISH_FAIL_CLOSED_REASON
    assert payload["diagnostics"]["kei_week1_reprice"]["applied_games"] == 0


def test_survivor_kei_overlay_week1_win_probs_ignore_kei_mix(monkeypatch) -> None:
    class _SurvivorSession:
        def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None):
            sql = " ".join(str(statement).split()).lower()
            if "from nfl_model_runtime_state" in sql:
                from tests.test_nfl_projection_endpoints import _Result

                return _Result([{"active_model_version": "nfl-v1.5-matchup-sim"}])
            if "spread_home" in sql:

                class _Mappings:
                    def all(self) -> list:
                        return [
                            {
                                "week": 1,
                                "season": 2026,
                                "home_abbr": "SEA",
                                "away_abbr": "NE",
                                "home_win_prob": 0.6189,
                                "away_win_prob": 0.3811,
                                "spread_home": -3.47,
                                "total_mean": 41.29,
                                "fair_home_ml": -162,
                                "fair_away_ml": 162,
                                "start_time": None,
                                "season_type": "REG",
                                "projection": None,
                            }
                        ]

                class _Exec:
                    def mappings(self) -> _Mappings:
                        return _Mappings()

                return _Exec()
            from tests.test_nfl_projection_endpoints import _Result

            return _Result([])

        def close(self) -> None:
            return None

    def _poison(**_kwargs: Any) -> tuple[dict, dict]:
        raise AssertionError("apply_week1_kei_reprice reached survivor publish path")

    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _SurvivorSession())
    monkeypatch.setattr(
        "src.services.nfl_kei_week1_reprice.apply_week1_kei_reprice",
        _poison,
    )
    if hasattr(nfl_routes, "apply_week1_kei_reprice"):
        monkeypatch.setattr(nfl_routes, "apply_week1_kei_reprice", _poison)

    lines = nfl_routes._load_kei_week_win_prob_lines(season=2026, week=1)
    assert len(lines) == 1
    row = lines[0]
    assert row["home_win_prob"] == 0.6189
    assert row["away_win_prob"] == 0.3811
    assert row["handicap_home_win_prob"] == 0.6189
    assert row["handicap_away_win_prob"] == 0.3811
