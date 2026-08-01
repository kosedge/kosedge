from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks  # noqa: E402


class _FakeResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeSession:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.params: list[dict] = []

    def execute(self, statement, params=None):  # noqa: ANN001
        self.statements.append(str(statement))
        self.params.append(dict(params or {}))
        return _FakeResult(rowcount=11)


def test_projection_is_pre_outcome_strict() -> None:
    ok = {
        "projection_created_at": datetime(2026, 5, 20, 16, 0, tzinfo=timezone.utc),
        "outcome_completed_at": datetime(2026, 5, 20, 23, 0, tzinfo=timezone.utc),
    }
    bad = {
        "projection_created_at": datetime(2026, 5, 21, 2, 0, tzinfo=timezone.utc),
        "outcome_completed_at": datetime(2026, 5, 20, 23, 0, tzinfo=timezone.utc),
    }
    assert tasks._projection_is_pre_outcome(ok) is True
    assert tasks._projection_is_pre_outcome(bad) is False
    assert tasks._count_leakage_violations([ok, bad, ok]) == 1


def test_repair_mlb_leakage_stamps_uses_least_clamp() -> None:
    session = _FakeSession()
    repaired = tasks._repair_mlb_leakage_stamps(
        session, model_version="mlb-v1-pa-sim", lookback_days=90
    )
    assert repaired == 11
    sql = " ".join(session.statements[0].lower().split())
    assert "least(" in sql
    assert "completed_at - interval '1 minute'" in sql
    assert session.params[0]["model_version"] == "mlb-v1-pa-sim"
    assert session.params[0]["lookback_days"] == 90
