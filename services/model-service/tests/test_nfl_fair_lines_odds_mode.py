"""WS-02 DUP-C / S1: fair-lines odds_mode skip|reuse must not call fetch_odds."""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.main import app
from src.routes import nfl as nfl_routes
from tests.test_nfl_projection_endpoints import _Session


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Session())
    return TestClient(app)


def test_resolve_reuse_with_events_never_calls_fetch_odds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    def _boom(**kwargs: Any) -> Any:
        calls.append(kwargs)
        raise AssertionError("fetch_odds must not be called on reuse")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    events = [
        {
            "id": "evt-1",
            "home_team": "Seattle Seahawks",
            "away_team": "New England Patriots",
            "bookmakers": [],
        }
    ]
    market, err, mode = nfl_routes._resolve_nfl_fair_lines_market_events(
        odds_mode="reuse",
        bookmakers="draftkings",
        supplied_events=events,
    )
    assert mode == "reuse"
    assert err is None
    assert market == events
    assert calls == []


def test_resolve_skip_never_calls_fetch_odds(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(**kwargs: Any) -> Any:
        raise AssertionError("fetch_odds must not be called on skip")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    market, err, mode = nfl_routes._resolve_nfl_fair_lines_market_events(
        odds_mode="skip",
        bookmakers="draftkings",
        supplied_events=None,
    )
    assert mode == "skip"
    assert err is None
    assert market == []


def test_get_odds_mode_skip_does_not_call_fetch_odds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**kwargs: Any) -> Any:
        raise AssertionError("fetch_odds must not be called on GET odds_mode=skip")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    response = client.get(
        "/nfl/fair-lines",
        params={"season": 2026, "days_ahead": 14, "persist": "0", "odds_mode": "skip"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnostics"]["odds_mode"] == "skip"
    assert payload["diagnostics"]["odds_persisted"]["snapshots_inserted"] == 0


def test_post_reuse_with_odds_payload_does_not_call_fetch_odds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**kwargs: Any) -> Any:
        raise AssertionError("fetch_odds must not be called on POST reuse+payload")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    response = client.post(
        "/nfl/fair-lines",
        params={"season": 2026, "days_ahead": 14, "persist": "0"},
        json={
            "odds_mode": "reuse",
            "odds_events": [],
            "odds_payload": [
                {"game": "New England Patriots @ Seattle Seahawks", "market": "Spread"}
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnostics"]["odds_mode"] == "reuse"
    assert payload["diagnostics"]["odds_persisted"]["events_persisted"] == 0
    assert payload["diagnostics"]["odds_persisted"]["snapshots_inserted"] == 0


def test_post_reuse_with_odds_events_does_not_call_fetch_odds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**kwargs: Any) -> Any:
        raise AssertionError("fetch_odds must not be called on POST reuse+events")

    monkeypatch.setattr(nfl_routes, "fetch_odds", _boom)
    response = client.post(
        "/nfl/fair-lines",
        params={"season": 2026, "days_ahead": 14, "persist": "0"},
        json={
            "odds_mode": "reuse",
            "odds_events": [
                {
                    "id": "evt-1",
                    "home_team": "Seattle Seahawks",
                    "away_team": "New England Patriots",
                    "bookmakers": [],
                }
            ],
            "odds_payload": [],
        },
    )
    assert response.status_code == 200
    assert response.json()["diagnostics"]["odds_mode"] == "reuse"
    assert response.json()["diagnostics"]["odds_events_seen"] == 1
