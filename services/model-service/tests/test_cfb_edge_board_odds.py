"""CFB Edge Board current-market acquire (warehouse reconstruct + fail closed)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_edge_board_odds import (
    reconstruct_events_from_warehouse_rows,
    current_cfb_odds_events,
)


def test_warehouse_rows_reconstruct_odds_api_events() -> None:
    rows = [
        {
            "external_id": "rut-bc",
            "start_time": datetime(2026, 9, 11, 23, 30, tzinfo=timezone.utc),
            "home_team": "Boston College Eagles",
            "away_team": "Rutgers Scarlet Knights",
            "book": "draftkings",
            "market": "spread",
            "spread_away": 13.5,
            "spread_home": -13.5,
            "price_away": -110,
            "price_home": -110,
            "captured_at": datetime(2026, 9, 10, 15, 0, tzinfo=timezone.utc),
        },
        {
            "external_id": "rut-bc",
            "start_time": datetime(2026, 9, 11, 23, 30, tzinfo=timezone.utc),
            "home_team": "Boston College Eagles",
            "away_team": "Rutgers Scarlet Knights",
            "book": "draftkings",
            "market": "total",
            "total_points": 52.5,
            "over_price": -110,
            "under_price": -110,
            "captured_at": datetime(2026, 9, 10, 15, 0, tzinfo=timezone.utc),
        },
    ]
    events = reconstruct_events_from_warehouse_rows(rows)
    assert len(events) == 1
    ev = events[0]
    assert ev["away_team"] == "Rutgers Scarlet Knights"
    assert ev["home_team"] == "Boston College Eagles"
    books = ev["bookmakers"]
    assert books[0]["key"] == "draftkings"
    keys = {m["key"] for m in books[0]["markets"]}
    assert keys == {"spreads", "totals"}
    spread = next(m for m in books[0]["markets"] if m["key"] == "spreads")
    away = next(o for o in spread["outcomes"] if o["name"].startswith("Rutgers"))
    assert away["point"] == 13.5


def test_empty_warehouse_without_live_fails_closed(monkeypatch) -> None:
    import src.services.cfb_edge_board_odds as mod

    monkeypatch.setattr(mod, "_load_warehouse_events", lambda _now: ([], None))
    payload = current_cfb_odds_events(
        now=datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc),
        allow_live=False,
    )
    assert payload["events"] == []
    assert payload["source"] == "none"
    assert payload["fresh"] is False
    assert payload["reason"] == "warehouse_empty"


def test_default_allow_live_is_false_on_warehouse_miss(monkeypatch) -> None:
    """G-CFB-RAIL-LIVE: default must not live-pull. Mutation: default True → fail."""
    import src.services.cfb_edge_board_odds as mod

    def _boom(*_a, **_k):
        raise AssertionError("fetch_odds must not run on default request path")

    monkeypatch.setattr(mod, "_load_warehouse_events", lambda _now: ([], None))
    monkeypatch.setattr(mod, "fetch_odds", _boom)
    payload = current_cfb_odds_events(
        now=datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc),
    )
    assert payload["source"] == "none"
    assert payload["events"] == []
    assert payload["reason"] == "warehouse_empty"


def test_cfb_edge_board_odds_route_never_live_pulls(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    import src.services.cfb_edge_board_odds as mod
    from src.main import app

    def _boom(*_a, **_k):
        raise AssertionError("fetch_odds must not run on /cfb/edge-board-odds")

    monkeypatch.setattr(mod, "_load_warehouse_events", lambda _now: ([], None))
    monkeypatch.setattr(mod, "fetch_odds", _boom)
    client = TestClient(app)
    response = client.get("/cfb/edge-board-odds")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "none"
    assert payload.get("events") == []
