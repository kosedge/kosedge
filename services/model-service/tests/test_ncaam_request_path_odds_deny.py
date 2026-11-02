"""G-NCAAM-PROXY: request-path NCAAM must not live-pull Odds when C8 unset."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routes import edge_board as edge_board_routes


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_ncaam_today_does_not_fetch_odds_when_c8_unset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ODDS_API_REQUEST_PATH_ALLOW", raising=False)

    async def _boom() -> list:
        raise AssertionError("_fetch_odds_ncaab must not run when C8 unset")

    monkeypatch.setattr(edge_board_routes, "_fetch_odds_ncaab", _boom)
    # Drop in-memory cache from other tests.
    edge_board_routes._CACHE["data"] = None
    edge_board_routes._CACHE["ts"] = 0.0
    response = client.get("/edge-board/ncaam/today")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rows"] == []
    assert payload.get("reason") == "paid_fetch_denied"
    assert payload.get("source") == "none"
