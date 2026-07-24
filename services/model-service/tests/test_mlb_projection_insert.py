"""Smoke tests for MLB projection insert (run-line columns + audit diagnostics)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import src.tasks as tasks


class _FakeResult:
    def fetchone(self):
        return (1,)


class _FakeSession:
    def __init__(self) -> None:
        self.statements: List[str] = []
        self.params: List[Dict[str, Any]] = []

    def execute(self, statement: Any, params: Optional[Dict[str, Any]] = None):
        sql = str(statement)
        self.statements.append(sql)
        self.params.append(params or {})
        if "information_schema.columns" in sql:
            return _FakeResult()
        return _FakeResult()


def test_insert_mlb_projection_persists_runline_and_shock_diagnostics(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "_MLB_PROJECTION_HAS_RUNLINE_COLS", None)
    session = _FakeSession()
    projection = {
        "game_id": "game-1",
        "model_version": "mlb-v1-pa-sim",
        "simulation_count": 100,
        "markets": {
            "f5_home_win_prob": 0.51,
            "fg_home_win_prob": 0.52,
            "f5_total_mean": 4.5,
            "fg_total_mean": 8.6,
            "fair_f5_home_ml": -105,
            "fair_fg_home_ml": -110,
            "fair_f5_total": 4.5,
            "fair_fg_total": 8.5,
            "fair_fg_spread_home": -1.5,
            "fair_f5_spread_home": -0.5,
            "fg_home_cover_prob_run_line": 0.48,
            "f5_home_cover_prob_run_line": 0.47,
            "fg_margin_mean": 0.35,
            "f5_margin_mean": 0.20,
        },
        "inputs": {"starter_home": "Ace"},
        "run_rates": {"full_home": 4.4},
        "diagnostics": {
            "lineup_shock": {"home_offense_mul": 1.02},
            "sp_change_shock": {"home": {"changed": 1.0}},
        },
    }
    tasks._insert_mlb_projection_and_audit(
        session,
        projection,
        seed=42,
        created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
    )
    assert len(session.statements) >= 2
    insert_sql = session.statements[1]
    assert "fair_fg_spread_home" in insert_sql
    assert "fg_home_cover_prob_run_line" in insert_sql
    insert_params = session.params[1]
    assert insert_params["fair_fg_spread_home"] == -1.5
    assert insert_params["fg_home_cover_prob_run_line"] == 0.48
    audit_params = session.params[2]
    diag = json.loads(audit_params["diagnostics"])
    assert "lineup_shock" in diag
    assert diag["sp_change_shock"]["home"]["changed"] == 1.0
